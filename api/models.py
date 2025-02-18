from tastypie.resources import ModelResource
from shop.models import Category, Course
from tastypie.authorization import Authorization
from .authentication import CustomAuthentication


class CategoryResource(ModelResource):
    class Meta:
        queryset = Category.objects.all()
        resource_name = 'categories'
        allowed_methods = ['get']

class CourseResource(ModelResource):
    class Meta:
        queryset = Course.objects.all()
        resource_name = 'courses'
        allowed_methods = ['get', 'post', 'delete']
        excludes = ['reviews_qty', 'created_at']
        authentication = CustomAuthentication()
        authorization = Authorization()

# приходять від клієнта і йдуть до сервера
    def hydrate(self,bundle): 
        bundle.obj.category_id = bundle.data['category_id']
        return bundle

# приходять від сервера і йдуть до клієнта
    def dehydrate(self, bundle):
        bundle.data['category_id'] = bundle.obj.category
        bundle.data['category'] = bundle.obj.category
        return bundle
    
    # приходять від сервера і йдуть до клієнта
    def dehydrate_title(self, bundle):
        return bundle.data['title'].upper()