from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db.models import Avg
from users.models import User

from listings.models import Item, ItemImage

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        user = self.user
        data['user'] = {
            'id': user.id,
            'email': user.email,
        }
        
        return data

class UserSerializer(serializers.ModelSerializer):
    rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'phone_number',
            'profile_picture',
            'country',
            'region',
            'city',
            'district',
            'street',
            'building',
            'apartment',
            'created_at',
            'updated_at',
            'rating',
            'reviews_count',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'rating', 'reviews_count')

    def get_rating(self, obj):
        from listings.models import Review
        avg_rating = Review.objects.filter(recipient=obj).aggregate(avg=Avg('rating'))['avg']
        return float(round(avg_rating, 2)) if avg_rating else None

    def get_reviews_count(self, obj):
        from listings.models import Review
        return Review.objects.filter(recipient=obj).count()

    def update(self, instance, validated_data):
        if 'profile_picture' in validated_data:
            if instance.profile_picture:
                instance.profile_picture.delete(save=False)
        return super().update(instance, validated_data)

# нужно ли обязательно указывать свой адрес при регистрации?
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            'email', 
            'username', 
            'password', 
            'password2', 
            'phone_number',
            'first_name',
            'last_name',
        )

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Password fields don't match."
            })
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        
        if not validated_data['username']:
            validated_data['username'] = validated_data['email'].split('@')[0]
        
        user = User.objects.create_user(**validated_data)
        return user

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, validators=[validate_password]
    )
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct")
        return value
    
    def update(self, instance, validated_data):
        instance.set_password(validated_data['new_password'])
        instance.save()
        return instance

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text='Refresh JWT token for adding to blacklist')


class ProfileItemImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemImage
        fields = ['url', 'alt_text']


class ProfileItemSerializer(serializers.ModelSerializer):
    # если нужно, чтобы подгружались все изображения, а не только main,
    # то изменить тут и prefetch во view
    image = ProfileItemImageSerializer(source="main_image_obj", read_only=True)

    class Meta:
        model = Item
        fields = [
            'id', 'name', 'price', 'status',
            'updated_at', 'image', 'description',
        ]


class ProfilePageSerializer(serializers.ModelSerializer):
    items = ProfileItemSerializer(source="owned_items", many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'profile_picture', 'first_name', 'last_name',
            'phone_number', 'email', 'items', # 'rating', 'reviews_count',
            'country', 'region', 'city', 'district',
        ]

    # ограничение на 20 айтемов. изменить / удалить если не нужно
    def get_items(self, obj):
        items_queryset = obj.owned_items.all()[:20]
        return ProfileItemSerializer(items_queryset, many=True, context=self.context).data