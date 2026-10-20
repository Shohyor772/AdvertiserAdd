from django.shortcuts import render
from .models import BloggerProfile

def blogger_list(request):
    bloggers = BloggerProfile.objects.all()
    return render(request, 'catalog/blogger_list.html', {'bloggers': bloggers})