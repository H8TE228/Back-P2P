from django.urls import path
from . import views

urlpatterns = [
    path('listings/<int:item_id>/transactions/', views.ItemTransactionView.as_view(), name='item_transaction'),
    path('transactions/<int:pk>/', views.TransactionDetailView.as_view(), name='transaction_detail'),
    path('transactions/', views.UserTransactionView.as_view(), name='transaction_list'),
    path('transactions/pending/', views.PendingTransactionsView.as_view(), name='pending_transaction_list'),
    path('transactions/<int:pk>/approve/', views.TransactionApprovalView.as_view(), name='approve_transaction'),
    path('transactions/<int:pk>/reject/', views.TransactionRejectionView.as_view(), name='reject_transaction'),
    path('transactions/<int:pk>/return/', views.ReturnItemView.as_view(), name='return_item'),
]