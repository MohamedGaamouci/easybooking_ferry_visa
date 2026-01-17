from django.contrib import admin
from .models import Agency, AgencyTag


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'city', 'phone', 'status')
    list_filter = ('status', 'city', 'tags')
    search_fields = ('company_name', 'phone')


@admin.register(AgencyTag)
class AgencyTagAdmin(admin.ModelAdmin):
    search_fields = ('name',)
