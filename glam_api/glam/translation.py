from modeltranslation.translator import translator, TranslationOptions
from .models import (Announcement, DataSource, Variable,
                     Product, CropMask, AdminLayer)

# for Announcement model


class AnnouncementTranslationOptions(TranslationOptions):
    fields = ['header', 'message']


class DataSourceTranslationOptions(TranslationOptions):
    fields = ['desc']


class VariableTranslationOptions(TranslationOptions):
    fields = ['display_name', 'desc']


class ProductTranslationOptions(TranslationOptions):
    fields = ['display_name', 'desc']


class CropMaskTranslationOptions(TranslationOptions):
    fields = ['display_name', 'desc']


class AdminLayerTranslationOptions(TranslationOptions):
    fields = ['display_name', 'desc']


translator.register(Announcement, AnnouncementTranslationOptions)
translator.register(DataSource, DataSourceTranslationOptions)
translator.register(Variable, VariableTranslationOptions)
translator.register(Product, ProductTranslationOptions)
translator.register(CropMask, CropMaskTranslationOptions)
translator.register(AdminLayer, AdminLayerTranslationOptions)
