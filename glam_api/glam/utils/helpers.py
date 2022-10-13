from django.utils.text import slugify


def get_closest_to_date(qs, date):
    greater = qs.filter(date__gte=date).order_by("date").first()
    less = qs.filter(date__lte=date).order_by("-date").first()

    if greater and less:
        return greater if abs(greater.date - date) < abs(less.date - date) else less
    else:
        return greater or less


def generate_unique_slug(instance, slug_field):
    name = instance.name.replace('.', '-')
    base_slug = slugify(name)
    slug = base_slug
    num = 1

    while type(instance).objects.filter(
            **{f'{slug_field}': f'{slug}'}).exists():
        slug = f'{base_slug}-{num}'
        num += 1

    unique_slug = slug
    return unique_slug
