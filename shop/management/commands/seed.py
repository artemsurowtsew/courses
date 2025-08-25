from django.core.management.base import BaseCommand
from shop.models import Category, Product
import random
import requests
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Seeds the database with sample data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # Create categories
        categories = [
            {'title': 'Електроніка', 'description': 'Гаджети та пристрої'},
            {'title': 'Книги', 'description': 'Друковані та цифрові книги'},
            {'title': 'Дім та кухня', 'description': 'Все для вашого дому'},
        ]
        
        Category.objects.all().delete()
        for cat_data in categories:
            Category.objects.create(**cat_data)

        self.stdout.write(self.style.SUCCESS('Категорії створено.'))

        # Create products
        products = [
            {'title': 'Смартфон X', 'category': 'Електроніка', 'price': 25000.00, 'stock': 50},
            {'title': 'Ноутбук Pro', 'category': 'Електроніка', 'price': 45000.00, 'stock': 30},
            {'title': 'Великий Роман', 'category': 'Книги', 'price': 550.00, 'stock': 100},
            {'title': 'Майстер Кулінарії', 'category': 'Книги', 'price': 750.00, 'stock': 80},
            {'title': 'Кавоварка', 'category': 'Дім та кухня', 'price': 2800.00, 'stock': 60},
            {'title': 'Потужний Блендер', 'category': 'Дім та кухня', 'price': 1600.00, 'stock': 90},
        ]

        Product.objects.all().delete()
        for prod_data in products:
            category = Category.objects.get(title=prod_data['category'])
            product = Product(
                title=prod_data['title'],
                description=f'Це високоякісний продукт: {prod_data["title"]}.',
                price=prod_data['price'],
                stock_quantity=prod_data['stock'],
                category=category,
                is_active=True,
                featured=random.choice([True, False])
            )
            
            # Add image from Unsplash service
            search_term = prod_data['title'].replace(' ', ',')
            image_url = f"https://source.unsplash.com/600x400/?{search_term}"
            response = requests.get(image_url, allow_redirects=True)
            if response.status_code == 200:
                product.image.save(f"{prod_data['title']}.png", ContentFile(response.content), save=True)
            
            product.save()

        self.stdout.write(self.style.SUCCESS('Товари створено.'))
        self.stdout.write(self.style.SUCCESS('Базу даних успішно заповнено!'))
