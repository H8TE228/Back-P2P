from django.db.models import Prefetch
from django.shortcuts import render
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import extend_schema

from .serializers import (
    CustomTokenObtainPairSerializer, 
    UserSerializer, 
    RegisterSerializer, 
    ChangePasswordSerializer,
    LogoutSerializer,
    ProfilePageSerializer
)

from listings.models import Item, ItemImage

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            serializer.update(user, serializer.validated_data)
            return Response(
                {"message": "Password updated successfully"},
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAdminUser,)


class LogoutView(generics.GenericAPIView):
    """
    Endpoint для выхода пользователя из системы.
    Требуется передать refresh токен для добавления в blacklist.
    """
    serializer_class = LogoutSerializer
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            refresh_token = serializer.validated_data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(
                {"error": "Invalid token"}, 
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(
        summary="Профиль пользователя по id",
        description="""
            Возвращает базовую информацию о пользователе и его товары
        """
    )
class ProfilePageView(generics.RetrieveAPIView):
    # queryset = User.objects.prefetch_related('owned_items__image')
    serializer_class = ProfilePageSerializer
    lookup_field = 'id'
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        main_images_qs = ItemImage.objects.filter(is_main=True)
        products_qs = Item.objects.prefetch_related(
            Prefetch('images', queryset=main_images_qs)
        ).order_by('-updated_at')
        return User.objects.prefetch_related(
            Prefetch('owned_items', queryset=products_qs)
        )


