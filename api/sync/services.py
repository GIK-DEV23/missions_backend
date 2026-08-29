import logging

from django.db import transaction, IntegrityError

from base.utils.exceptions import CustomValidationError
from souls import services as soul_services
from souls.models import Soul, ProgressUpdate
from testimonies import services as testimony_services
from testimonies.models import Testimony, Miracle
from sync.constants import SyncEntity, SyncOp, SyncMutationStatus
from sync.models import SyncMutation

logger = logging.getLogger(__name__)


class SyncConflict(Exception):
    """Raised when an update/delete targets a client_id with no matching record."""


def _handle_soul(user, op, client_id, payload):
    if op == SyncOp.CREATE:
        payload["client_id"] = client_id
        return soul_services.create_soul(payload)

    soul = Soul.objects.filter(client_id=client_id).first()
    if not soul:
        raise SyncConflict("No soul found for client_id '{}'".format(client_id))
    soul_services.missioner_soul_operations_handler(user, {"soul_id": soul.id})

    if op == SyncOp.UPDATE:
        return soul_services.update_soul(user=user, soul_id=soul.id, data=payload)
    if op == SyncOp.DELETE:
        return soul_services.delete_soul(user=user, soul_id=soul.id)
    raise CustomValidationError("Unsupported op '{}'".format(op))


def _handle_check_in(user, op, client_id, payload):
    if op == SyncOp.CREATE:
        payload["client_id"] = client_id
        return soul_services.create_progress_update(payload)

    progress_update = ProgressUpdate.objects.filter(client_id=client_id).first()
    if not progress_update:
        raise SyncConflict("No check-in found for client_id '{}'".format(client_id))
    soul_services.progress_update_handler(user, {"soul_id": progress_update.soul_id})

    if op == SyncOp.UPDATE:
        return soul_services.update_progress_update(progress_update.id, payload)
    if op == SyncOp.DELETE:
        return soul_services.delete_progress_update(progress_update.id)
    raise CustomValidationError("Unsupported op '{}'".format(op))


def _handle_testimony(user, op, client_id, payload):
    if op == SyncOp.CREATE:
        payload["client_id"] = client_id
        return testimony_services.create_testimony(payload)

    testimony = Testimony.objects.filter(client_id=client_id).first()
    if not testimony:
        raise SyncConflict("No testimony found for client_id '{}'".format(client_id))
    testimony_services.miracle_and_testimony_handler(user, {"soul_id": testimony.soul_id})

    if op == SyncOp.UPDATE:
        return testimony_services.update_testimony(testimony.id, payload)
    if op == SyncOp.DELETE:
        return testimony_services.delete_testimony(testimony.id)
    raise CustomValidationError("Unsupported op '{}'".format(op))


def _handle_miracle(user, op, client_id, payload):
    if op == SyncOp.CREATE:
        payload["client_id"] = client_id
        return testimony_services.create_miracle(payload)

    miracle = Miracle.objects.filter(client_id=client_id).first()
    if not miracle:
        raise SyncConflict("No miracle found for client_id '{}'".format(client_id))
    testimony_services.miracle_and_testimony_handler(user, {"soul_id": miracle.soul_id})

    if op == SyncOp.UPDATE:
        return testimony_services.update_miracle(miracle.id, payload)
    if op == SyncOp.DELETE:
        return testimony_services.delete_miracle(miracle.id)
    raise CustomValidationError("Unsupported op '{}'".format(op))


ENTITY_DISPATCH = {
    SyncEntity.SOUL: _handle_soul,
    SyncEntity.CHECK_IN: _handle_check_in,
    SyncEntity.TESTIMONY: _handle_testimony,
    SyncEntity.MIRACLE: _handle_miracle,
}


def _duplicate_result(existing: SyncMutation) -> dict:
    return {
        "client_mutation_id": existing.client_mutation_id,
        "status": SyncMutationStatus.DUPLICATE,
        "id": existing.result_id,
        "client_id": str(existing.result_client_id) if existing.result_client_id else None,
        "error": existing.error,
    }


def _finalize(client_mutation_id, entity, op, user, status, result_id=None, result_client_id=None, error=None) -> dict:
    with transaction.atomic():
        record = SyncMutation.objects.create(
            user=user,
            client_mutation_id=client_mutation_id,
            entity=entity,
            op=op,
            status=status,
            result_id=result_id,
            result_client_id=result_client_id,
            error=error,
        )
    return {
        "client_mutation_id": record.client_mutation_id,
        "status": record.status,
        "id": record.result_id,
        "client_id": str(record.result_client_id) if record.result_client_id else None,
        "error": record.error,
    }


def apply_mutation(user, mutation: dict) -> dict:
    client_mutation_id = mutation["client_mutation_id"]
    entity = mutation["entity"]
    client_id = mutation["client_id"]
    op = mutation["op"]
    payload = dict(mutation.get("payload") or {})

    existing = SyncMutation.objects.filter(client_mutation_id=client_mutation_id).first()
    if existing:
        return _duplicate_result(existing)

    handler = ENTITY_DISPATCH.get(entity)
    if handler is None:
        return _finalize(client_mutation_id, entity, op, user, SyncMutationStatus.REJECTED,
                          error="Unknown entity '{}'".format(entity))

    try:
        with transaction.atomic():
            obj = handler(user, op, client_id, payload)
            result_client_id = getattr(obj, "client_id", None) or client_id
            return _finalize(client_mutation_id, entity, op, user, SyncMutationStatus.APPLIED,
                              result_id=obj.id, result_client_id=result_client_id)
    except IntegrityError:
        # A concurrent retry raced us on the same client_mutation_id.
        existing = SyncMutation.objects.filter(client_mutation_id=client_mutation_id).first()
        if existing:
            return _duplicate_result(existing)
        return _finalize(client_mutation_id, entity, op, user, SyncMutationStatus.REJECTED,
                          error="Duplicate or conflicting record")
    except SyncConflict as e:
        return _finalize(client_mutation_id, entity, op, user, SyncMutationStatus.CONFLICT, error=str(e))
    except CustomValidationError as e:
        return _finalize(client_mutation_id, entity, op, user, SyncMutationStatus.REJECTED, error=str(e.errors))
    except Exception:
        logger.exception("Unexpected error applying sync mutation %s", client_mutation_id)
        return _finalize(client_mutation_id, entity, op, user, SyncMutationStatus.REJECTED, error="Unexpected error")


def apply_mutations(user, mutations: list) -> list:
    return [apply_mutation(user, m) for m in mutations]
