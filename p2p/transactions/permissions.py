from rest_framework import permissions

from .models import Transaction

class CanApproveTransaction(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        owner_approve = [Transaction.Status.PENDING, Transaction.Status.RETURING]
        if request.user == obj.owner and obj.status in owner_approve:
            return True
        renter_approve = Transaction.Status.APPROVED
        if request.user == obj.renter and obj.status == renter_approve:
            return True
        return False
    

class CanReturnItem(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            request.user == obj.renter and
            obj.status == Transaction.Status.ACTIVE
        )