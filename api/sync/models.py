from django.db import models

from base.models import BaseModel, client_id_field


class SyncMutation(BaseModel):
    """Idempotency ledger — one row per client_mutation_id ever processed."""
    user = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="sync_mutations"
    )
    client_mutation_id = models.CharField(max_length=64, unique=True, db_index=True)
    entity = models.CharField(max_length=30)
    op = models.CharField(max_length=10)
    status = models.CharField(max_length=10)
    result_id = models.IntegerField(null=True, blank=True)
    result_client_id = client_id_field(unique=False)
    error = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "sync_mutations"

    def __str__(self):
        return "{} ({})".format(self.client_mutation_id, self.status)
