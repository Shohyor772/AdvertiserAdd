from django.db.models import Avg, Count, Q
from rest_framework import serializers
from .models import BloggerProfile


class SearchParams(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True, max_length=120)
    platform = serializers.CharField(required=False, allow_blank=True, max_length=50)
    category = serializers.CharField(required=False, allow_blank=True, max_length=100)
    city = serializers.CharField(required=False, allow_blank=True, max_length=120)
    price_min = serializers.IntegerField(required=False, min_value=0)
    price_max = serializers.IntegerField(required=False, min_value=0)
    subscribers_min = serializers.IntegerField(required=False, min_value=0)
    subscribers_max = serializers.IntegerField(required=False, min_value=0)
    female_percent = serializers.IntegerField(required=False, min_value=0, max_value=100)
    male_percent = serializers.IntegerField(required=False, min_value=0, max_value=100)
    age_min = serializers.IntegerField(required=False, min_value=0, max_value=100)
    age_max = serializers.IntegerField(required=False, min_value=0, max_value=100)
    verified = serializers.BooleanField(required=False)
    ordering = serializers.ChoiceField(required=False, choices=['price', '-price', 'subscribers', '-subscribers', '-rating', 'rating', 'username'])
    def validate(self, data):
        for key in ['price', 'subscribers', 'age']:
            if key+'_min' in data and key+'_max' in data and data[key+'_min'] > data[key+'_max']:
                raise serializers.ValidationError('Нижняя граница диапазона не может быть больше верхней.')
        return data


def search_bloggers(params):
    s = SearchParams(data=params)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    qs = BloggerProfile.objects.filter(user__is_active=True).select_related('user').annotate(rating_value=Avg('user__received_reviews__rating'), reviews_count=Count('user__received_reviews', distinct=True))
    if d.get('q'):
        qs = qs.filter(Q(user__username__icontains=d['q']) | Q(user__first_name__icontains=d['q']))
    for f in ['platform', 'category', 'city']:
        if d.get(f):
            qs = qs.filter(**{f+'__iexact': d[f]})
    for f in ['price', 'subscribers']:
        for bound, lookup in [('min', 'gte'), ('max', 'lte')]:
            if f+'_'+bound in d:
                qs = qs.filter(**{f+'__'+lookup: d[f+'_'+bound]})
    if 'female_percent' in d:
        qs = qs.filter(female_percent__gte=d['female_percent'])
    if 'male_percent' in d:
        qs = qs.filter(female_percent__lte=100-d['male_percent'])
    if 'age_min' in d:
        qs = qs.filter(age_min__gte=d['age_min'])
    if 'age_max' in d:
        qs = qs.filter(age_max__lte=d['age_max'])
    if d.get('verified'):
        qs = qs.filter(is_verified=True)
    ordering = {'-rating': '-rating_value', 'rating': 'rating_value', 'username': 'user__username'}.get(d.get('ordering'), d.get('ordering', '-subscribers'))
    return qs.order_by(ordering, 'id')
