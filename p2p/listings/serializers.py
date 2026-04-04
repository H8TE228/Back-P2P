from rest_framework import serializers
from .models import Category, Listing, ListingImage

class ListingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = ['id', 'image', 'is_primary', 'uploaded_at']
        read_only_fields = ['uploaded_at']

class CategorySerializer(serializers.ModelSerializer):
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent', 'children_count']
        read_only_fields = ['children_count']

    def get_children_count(self, obj):
        return obj.children.count()

class ListingSerializer(serializers.ModelSerializer):
    owner_name = serializers.ReadOnlyField(source='owner.username')
    category_name = serializers.ReadOnlyField(source='category.name')
    images = ListingImageSerializer(many=True, read_only=True)
    
    # Поле для загрузки новых изображений
    new_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Listing
        fields = [
            'id', 'title', 'description', 'price', 'category', 'category_name',
            'owner', 'owner_name', 'status', 'created_at', 'updated_at',
            'images', 'new_images'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at', 'category_name', 'owner_name']

    # def create(self, validated_data):
    #     new_images_data = validated_data.pop('new_images', [])
    #     listing = Listing.objects.create(**validated_data)
        
    #     for image_data in new_images:
    #         ListingImage.objects.create(listing=listing, image=image_data)
        
    #     return listing

    def update(self, instance, validated_data):
        new_images_data = validated_data.pop('new_images', [])
        instance = super().update(instance, validated_data)
        
        for image_data in new_images_data:
            ListingImage.objects.create(listing=instance, image=image_data)
        
        return instance