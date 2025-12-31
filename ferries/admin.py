from django.contrib import admin
from .models import Provider, Port, ProviderRoute, FerryRequest


@admin.register(ProviderRoute)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('provider', 'origin', 'destination', 'is_active')
    list_filter = ('provider',)


@admin.register(FerryRequest)
class FerryRequestAdmin(admin.ModelAdmin):
    list_display = ('reference', 'agency', 'departure_date', 'status')
    list_filter = ('status', 'trip_type')
    search_fields = ('reference', 'agency__company_name')


admin.site.register(Provider)
admin.site.register(Port)
