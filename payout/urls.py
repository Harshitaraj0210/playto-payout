from django.urls import path
from . import views

urlpatterns = [
    path('merchants/', views.merchant_list, name='merchant-list'),
    path('merchants/<uuid:merchant_id>/', views.merchant_detail, name='merchant-detail'),
    path('merchants/<uuid:merchant_id>/payouts/', views.payout_list, name='payout-list'),
    path('merchants/<uuid:merchant_id>/payouts/request/', views.request_payout, name='request-payout'),
    path('payouts/<uuid:payout_id>/', views.payout_detail, name='payout-detail'),
]