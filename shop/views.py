from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg
from django.core.paginator import Paginator
from .models import Product, Category, Cart, CartItem, Order, OrderItem, Review, Wishlist
import json
from django.conf import settings
from liqpay.liqpay import LiqPay
from django.views.decorators.csrf import csrf_exempt


def about(request):
    """Display the about page"""
    return render(request, 'shop/about.html')


def contact(request):
    """Display the contact page"""
    return render(request, 'shop/contact.html')


def index(request):
    """Display all products with filtering and pagination"""
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.all()
    
    # Filter by category
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Sort products
    sort_by = request.GET.get('sort', 'created_at')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('title')
    else:
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Featured products
    featured_products = Product.objects.filter(featured=True, is_active=True)[:4]
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'featured_products': featured_products,
        'current_category': category_id,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    return render(request, 'shop/products.html', context)


def product_detail(request, product_id):
    """Display single product details"""
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    reviews = product.reviews.all().order_by('-created_at')
    related_products = Product.objects.filter(
        category=product.category, 
        is_active=True
    ).exclude(id=product.id)[:4]
    
    # Calculate average rating
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    
    context = {
        'product': product,
        'reviews': reviews,
        'related_products': related_products,
        'avg_rating': avg_rating,
    }
    return render(request, 'shop/product_detail.html', context)


def add_to_cart(request, product_id):
    """Add product to cart"""
    product = get_object_or_404(Product, pk=product_id)
    quantity = int(request.POST.get('quantity', 1))

    if quantity > product.stock_quantity:
        messages.error(request, 'Not enough stock available.')
        return redirect('shop:product_detail', product_id=product_id)

    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        session_cart = request.session.get('cart', {})
        cart_id = session_cart.get('id')
        if cart_id:
            cart, _ = Cart.objects.get_or_create(id=cart_id, user=None)
        else:
            cart = Cart.objects.create(user=None)
            request.session['cart'] = {'id': cart.id}

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )

    if not created:
        cart_item.quantity += quantity
        if cart_item.quantity > product.stock_quantity:
            cart_item.quantity = product.stock_quantity
        cart_item.save()

    messages.success(request, f'{product.title} added to your cart.')
    return redirect('shop:cart')


def cart_view(request):
    """Display cart contents"""
    cart = None
    cart_items = []
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all()
        except Cart.DoesNotExist:
            pass  # No cart for this user yet
    else:
        session_cart = request.session.get('cart')
        if session_cart:
            try:
                cart = Cart.objects.get(id=session_cart.get('id'), user=None)
                cart_items = cart.items.all()
            except Cart.DoesNotExist:
                pass  # Stale session data

    context = {
        'cart_items': cart_items,
        'cart': cart,
    }
    return render(request, 'shop/cart.html', context)


@login_required
def update_cart(request, item_id):
    """Update cart item quantity"""
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity <= 0:
            cart_item.delete()
            messages.success(request, 'Item removed from cart.')
        elif quantity > cart_item.product.stock_quantity:
            messages.error(request, 'Not enough stock available.')
        else:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Cart updated.')
    
    return redirect('shop:cart')


@login_required
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('shop:cart')


@login_required
def checkout(request):
    """Checkout process"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.all()
        if not cart_items:
            messages.error(request, 'Your cart is empty.')
            return redirect('shop:cart')
    except Cart.DoesNotExist:
        messages.error(request, 'Your cart is empty.')
        return redirect('shop:cart')
    
    if request.method == 'POST':
        # Create order
        order = Order.objects.create(
            user=request.user,
            total_amount=cart.total_price,
            shipping_address=request.POST.get('shipping_address'),
            billing_address=request.POST.get('billing_address'),
            phone=request.POST.get('phone'),
            email=request.POST.get('email'),
            notes=request.POST.get('notes', ''),
        )
        
        # Create order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.get_price,
            )
            # Update stock
            cart_item.product.stock_quantity -= cart_item.quantity
            cart_item.product.save()
        
        # Clear cart
        cart_items.delete()
        
        messages.success(request, f'Order {order.order_number} placed successfully!')
        return redirect('shop:payment', order_id=order.id)
    
    context = {
        'cart_items': cart_items,
        'cart': cart,
    }
    return render(request, 'shop/checkout.html', context)


@login_required
def order_detail(request, order_id):
    """Display order details"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {'order': order}
    return render(request, 'shop/order_detail.html', context)


@login_required
def order_history(request):
    """Display user's order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {'orders': orders}
    return render(request, 'shop/order_history.html', context)


@login_required
def add_review(request, product_id):
    """Add product review"""
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=product_id)
        rating = int(request.POST.get('rating'))
        comment = request.POST.get('comment')
        
        review, created = Review.objects.get_or_create(
            product=product,
            user=request.user,
            defaults={'rating': rating, 'comment': comment}
        )
        
        if not created:
            review.rating = rating
            review.comment = comment
            review.save()
            messages.success(request, 'Review updated successfully.')
        else:
            messages.success(request, 'Review added successfully.')
    
    return redirect('shop:product_detail', product_id=product_id)


@login_required
def wishlist_view(request):
    """Display user's wishlist"""
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    context = {'wishlist': wishlist}
    return render(request, 'shop/wishlist.html', context)


@login_required
def add_to_wishlist(request, product_id):
    """Add product to wishlist"""
    product = get_object_or_404(Product, pk=product_id)
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    
    if product in wishlist.products.all():
        wishlist.products.remove(product)
        messages.success(request, f'{product.title} removed from wishlist.')
    else:
        wishlist.products.add(product)
        messages.success(request, f'{product.title} added to wishlist.')
    
    return redirect('shop:product_detail', product_id=product_id)


@login_required
def payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    liqpay = LiqPay(settings.LIQPAY_PUBLIC_KEY, settings.LIQPAY_PRIVATE_KEY, host='https://www.liqpay.ua/api/')
    params = {
        'action': 'pay',
        'amount': str(order.total_amount),
        'currency': 'UAH',
        'description': f'Payment for order #{order.order_number}',
        'order_id': str(order.id),
        'version': '3',
        'result_url': request.build_absolute_uri(f'/shop/order/{order.id}/'),
        'server_url': request.build_absolute_uri('/shop/liqpay-callback/'),
    }
    form = liqpay.cnb_form(params)
    return render(request, 'shop/payment.html', {'form': form})


@csrf_exempt
def liqpay_callback(request):
    if request.method == 'POST':
        data = request.POST.get('data')
        signature = request.POST.get('signature')
        
        liqpay = LiqPay(settings.LIQPAY_PUBLIC_KEY, settings.LIQPAY_PRIVATE_KEY)
        sign = liqpay.str_to_sign(settings.LIQPAY_PRIVATE_KEY + data + settings.LIQPAY_PRIVATE_KEY)
        
        if sign == signature:
            response = liqpay.decode_data_from_str(data)
            order_id = response.get('order_id')
            status = response.get('status')
            
            if status == 'success':
                order = Order.objects.get(id=order_id)
                order.status = 'processing'
                order.save()
                
    return HttpResponse(status=200)
