from tastypie.resources import ModelResource
from shop.models import Category, Product, Cart, CartItem, Order, OrderItem
from tastypie.authorization import Authorization
from tastypie.authentication import Authentication
from .authentication import CustomAuthentication
from tastypie import fields


class CategoryResource(ModelResource):
    class Meta:
        queryset = Category.objects.all()
        resource_name = 'categories'
        allowed_methods = ['get']


class ProductResource(ModelResource):
    category = fields.ForeignKey('api.models.CategoryResource', 'category', full=True)
    
    class Meta:
        queryset = Product.objects.filter(is_active=True)
        resource_name = 'products'
        allowed_methods = ['get', 'post', 'put', 'delete']
        excludes = ['created_at', 'updated_at']
        authentication = CustomAuthentication()
        authorization = Authorization()
        filtering = {
            'category': ['exact'],
            'featured': ['exact'],
            'price': ['range', 'gt', 'gte', 'lt', 'lte'],
            'title': ['icontains'],
        }
        ordering = ['title', 'price', 'created_at']

    def hydrate(self, bundle): 
        if 'category_id' in bundle.data:
            bundle.obj.category_id = bundle.data['category_id']
        return bundle

    def dehydrate(self, bundle):
        bundle.data['category_id'] = bundle.obj.category.id
        bundle.data['category_name'] = bundle.obj.category.title
        bundle.data['in_stock'] = bundle.obj.in_stock
        bundle.data['is_on_sale'] = bundle.obj.is_on_sale
        bundle.data['current_price'] = float(bundle.obj.get_price)
        return bundle


class CartResource(ModelResource):
    items = fields.ToManyField('api.models.CartItemResource', 'items', full=True)
    
    class Meta:
        queryset = Cart.objects.all()
        resource_name = 'cart'
        allowed_methods = ['get', 'post', 'put', 'delete']
        authentication = CustomAuthentication()
        authorization = Authorization()
    
    def dehydrate(self, bundle):
        bundle.data['total_price'] = float(bundle.obj.total_price)
        bundle.data['total_items'] = bundle.obj.total_items
        return bundle


class CartItemResource(ModelResource):
    product = fields.ForeignKey(ProductResource, 'product', full=True)
    cart = fields.ForeignKey(CartResource, 'cart')
    
    class Meta:
        queryset = CartItem.objects.all()
        resource_name = 'cart-items'
        allowed_methods = ['get', 'post', 'put', 'delete']
        authentication = CustomAuthentication()
        authorization = Authorization()
    
    def dehydrate(self, bundle):
        bundle.data['total_price'] = float(bundle.obj.total_price)
        return bundle


class OrderResource(ModelResource):
    items = fields.ToManyField('api.models.OrderItemResource', 'items', full=True)
    
    class Meta:
        queryset = Order.objects.all()
        resource_name = 'orders'
        allowed_methods = ['get', 'post']
        excludes = ['created_at', 'updated_at']
        authentication = CustomAuthentication()
        authorization = Authorization()
        filtering = {
            'status': ['exact'],
            'user': ['exact'],
        }
        ordering = ['-created_at']


class OrderItemResource(ModelResource):
    product = fields.ForeignKey(ProductResource, 'product', full=True)
    order = fields.ForeignKey(OrderResource, 'order')
    
    class Meta:
        queryset = OrderItem.objects.all()
        resource_name = 'order-items'
        allowed_methods = ['get']
        authentication = CustomAuthentication()
        authorization = Authorization()
    
    def dehydrate(self, bundle):
        bundle.data['total_price'] = float(bundle.obj.total_price)
        return bundle
