from tastypie.api import Api
from api.models import (
    CategoryResource, 
    ProductResource, 
    CartResource, 
    CartItemResource, 
    OrderResource, 
    OrderItemResource
)
from django.urls import path, include

api = Api(api_name='v1')
api.register(CategoryResource())
api.register(ProductResource())
api.register(CartResource())
api.register(CartItemResource())
api.register(OrderResource())
api.register(OrderItemResource())

urlpatterns = [
    path('', include(api.urls), name='index')
]
