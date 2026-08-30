import ast
from typing import Any, Dict

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.http import HttpRequest
from phonenumber_field.modelfields import PhoneNumberField


class ToDictMixin:
    """
    A mixin that provides a `to_dict()` method to
    represent a model as a dictionary. This will simply
    add representations of non-relational fields. Relational
    fields should be handled on the model, as doing it here
    in any kind of generic way quickly leads to endless loops
    and a ton of needless complexity.
    """

    def to_dict(self, request: HttpRequest = None) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        # Process concrete fields only (not GFK or m2m)
        for field in self._meta.concrete_fields:
            # Handling FKs is up to the implementer
            if field.many_to_one or field.one_to_one:
                continue

            data[field.name] = field.value_from_object(self)

            if isinstance(field, models.DateTimeField):
                if data[field.name]:
                    data[field.name] = data[field.name].astimezone().isoformat()

            if isinstance(field, models.DateField):
                if data[field.name]:
                    data[field.name] = str(data[field.name])

            # Use the file name for FileFields (includes ImageFields)
            # and include a url field as well
            elif isinstance(field, models.FileField):
                file = field.value_from_object(self)
                if file:
                    data[field.name] = request.build_absolute_uri(file.url) if request else file.url
                else:
                    data[field.name] = None

            elif isinstance(field, PhoneNumberField):
                if data[field.name]:
                    data[field.name] = str(data[field.name])

            elif isinstance(field, models.UUIDField):
                if data[field.name]:
                    data[field.name] = str(data[field.name])

        # Tack on the url for good measure
        if hasattr(self, "get_absolute_url"):
            data["url"] = self.get_absolute_url()  # type: ignore

        return data


def client_id_field(**overrides):
    """UUID an offline client assigns a record at creation time, before it has a server id."""
    options = dict(null=True, blank=True, unique=True, db_index=True)
    options.update(overrides)
    return models.UUIDField(**options)


class BaseModel(models.Model, ToDictMixin):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)

    def self_content_type(self):
        return ContentType.objects.get_for_model(self)

    @property
    def type_name(self):
        content_type = self.self_content_type()
        return f"{content_type.app_label}.{content_type.model}"

    @property
    def type_id(self):
        return self.self_content_type().id

    class Meta:
        abstract = True
        ordering = ("-created_at",)
