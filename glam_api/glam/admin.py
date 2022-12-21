from django.contrib import admin

from modeltranslation.admin import TranslationAdmin

from .models import (Tag, DataSource, Variable, Colormap, Crop,
                     Product, CropMask, BoundaryLayer, Announcement,
                     ImageExport)


class AnnouncementAdmin(TranslationAdmin):
    pass


class SourceAdmin(TranslationAdmin):
    pass


class VariableAdmin(TranslationAdmin):
    pass


class ProductAdmin(TranslationAdmin):
    pass


class CropMaskAdmin(TranslationAdmin):
    pass


class BoundaryLayerAdmin(TranslationAdmin):
    pass


admin.site.register(Tag)
admin.site.register(Announcement, AnnouncementAdmin)
admin.site.register(DataSource, SourceAdmin)
admin.site.register(Variable, VariableAdmin)
admin.site.register(Colormap)
admin.site.register(Crop)
admin.site.register(Product, ProductAdmin)
admin.site.register(CropMask, CropMaskAdmin)
admin.site.register(BoundaryLayer, BoundaryLayerAdmin)
admin.site.register(ImageExport)
