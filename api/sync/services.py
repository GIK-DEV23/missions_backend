import logging

from django.db import transaction, IntegrityError

from authentication.permissions import has_role_type
from base.utils.exceptions import CustomValidationError
from souls import services as soul_services
from souls.models import Soul, ProgressUpdate
from testimonies import services as testimony_services
from testimonies.models import Testimony, Miracle
from sync.constants import SyncEntity, SyncOp, SyncMutationStatus
from sync.models import SyncMutation

logger = logging.getLogger(__name__)

MAX_CLIENT_MUTATION_ID_LEN = SyncMutation._meta.get_field("client_mutation_id").max_length
MAX_ENTITY_LEN = SyncMutation._meta.get_field("entity").max_length
MAX_OP_LEN = SyncMutation._meta.get_field("op").max_length


class SyncConflict(Exception):
    """Raised when an update/delete targets a client_id with no matching record."""


def _is_restricted_to_own_records(user) -> bool:
    """Mirrors require_permission's gating: the ownership check only applies
    when every role the user holds is missioner_template (never for admins/staff/exec)."""
    if user.is_superuser or has_role_type("superuser", user=user) or has_role_type("admin", user=user):
        return False
    role_names = [r.name.lower() for r in user.roles.all()]
    if not role_names:
        return False
    return all(name == "missioner_template" for name in role_names)


def _user_has_permission(user, tag: str) -> bool:
    if user.is_superuser or has_role_type("superuser", user=user) or has_role_type("admin", user=user):
        return True
    permissions = set()
    for role in user.roles.all():
        if role.permissions:
            permissions.update(role.permissions)
    return tag in permissions


# --- Soul -------------------------------------------------------------

def _create_soul(user, client_id, payload):
    payload["client_id"] = client_id
    obj = soul_services.create_soul(payload)
    return obj, obj.id


def _update_soul(user, target, payload):
    obj = soul_services.update_soul(user=user, soul_id=target.id, data=payload)
    return obj, obj.id


def _delete_soul(user, target, payload):
    target_id = target.id
    soul_services.delete_soul(user=user, soul_id=target.id)
    return None, target_id


def _check_soul_ownership(user, target):
    if _is_restricted_to_own_records(user):
        soul_services.missioner_soul_operations_handler(user, {"soul_id": target.id})


# --- Check-in (ProgressUpdate) -----------------------------------------

def _create_check_in(user, client_id, payload):
    payload["client_id"] = client_id
    obj = soul_services.create_progress_update(payload)
    return obj, obj.id


def _update_check_in(user, target, payload):
    obj = soul_services.update_progress_update(target.id, payload)
    return obj, obj.id


def _delete_check_in(user, target, payload):
    target_id = target.id
    soul_services.delete_progress_update(target.id)
    return None, target_id


def _check_check_in_ownership(user, target):
    if _is_restricted_to_own_records(user):
        soul_services.progress_update_handler(user, {"soul_id": target.soul_id})


# --- Testimony -----------------------------------------------------------

def _create_testimony(user, client_id, payload):
    payload["client_id"] = client_id
    obj = testimony_services.create_testimony(payload)
    return obj, obj.id


def _update_testimony(user, target, payload):
    obj = testimony_services.update_testimony(target.id, payload)
    return obj, obj.id


def _delete_testimony(user, target, payload):
    target_id = target.id
    testimony_services.delete_testimony(target.id)
    return None, target_id


def _check_testimony_ownership(user, target):
    if _is_restricted_to_own_records(user):
        testimony_services.miracle_and_testimony_handler(user, {"soul_id": target.soul_id})


# --- Miracle -----------------------------------------------------------

def _create_miracle(user, client_id, payload):
    payload["client_id"] = client_id
    obj = testimony_services.create_miracle(payload)
    return obj, obj.id


def _update_miracle(user, target, payload):
    obj = testimony_services.update_miracle(target.id, payload)
    return obj, obj.id


def _delete_miracle(user, target, payload):
    target_id = target.id
    testimony_services.delete_miracle(target.id)
    return None, target_id


def _check_miracle_ownership(user, target):
    if _is_restricted_to_own_records(user):
        testimony_services.miracle_and_testimony_handler(user, {"soul_id": target.soul_id})


ENTITY_REGISTRY = {
    SyncEntity.SOUL: {
        "model": Soul,
        "create": _create_soul,
        "update": _update_soul,
        "delete": _delete_soul,
        "check_ownership": _check_soul_ownership,
        "permissions": {
            SyncOp.CREATE: "create_soul",
            SyncOp.UPDATE: "update_soul",
            SyncOp.DELETE: "delete_soul",
        },
    },
    SyncEntity.CHECK_IN: {
        "model": ProgressUpdate,
        "create": _create_check_in,
        "update": _update_check_in,
        "delete": _delete_check_in,
        "check_ownership": _check_check_in_ownership,
        "permissions": {
            SyncOp.CREATE: "create_progress_update",
            SyncOp.UPDATE: "update_progress_update",
            SyncOp.DELETE: "delete_progress_update",
        },
    },
    SyncEntity.TESTIMONY: {
        "model": Testimony,
        "create": _create_testimony,
        "update": _update_testimony,
        "delete": _delete_testimony,
        "check_ownership": _check_testimony_ownership,
        "permissions": {
            SyncOp.CREATE: "create_testimony",
            SyncOp.UPDATE: "update_testimony",
            SyncOp.DELETE: "delete_testimony",
        },
    },
    SyncEntity.MIRACLE: {
        "model": Miracle,
        "create": _create_miracle,
        "update": _update_miracle,
        "delete": _delete_miracle,
        "check_ownership": _check_miracle_ownership,
        "permissions": {
            SyncOp.CREATE: "create_miracle",
            SyncOp.UPDATE: "update_miracle",
            SyncOp.DELETE: "delete_miracle",
        },
    },
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


def _fallback_result(client_mutation_id, error) -> dict:
    """Used only if even _finalize() itself fails — never raise out of apply_mutation."""
    return {
        "client_mutation_id": client_mutation_id,
        "status": SyncMutationStatus.REJECTED,
        "id": None,
        "client_id": None,
        "error": error,
    }


def apply_mutation(user, mutation: dict) -> dict:
    client_mutation_id = str(mutation["client_mutation_id"])[:MAX_CLIENT_MUTATION_ID_LEN]
    entity = str(mutation["entity"])[:MAX_ENTITY_LEN]
    op = str(mutation["op"])[:MAX_OP_LEN]
    client_id = mutation["client_id"]
    payload = dict(mutation.get("payload") or {})

    try:
        existing = SyncMutation.objects.filter(client_mutation_id=client_mutation_id).first()
        if existing:
            return _duplicate_result(existing)

        config = ENTITY_REGISTRY.get(entity)
        if config is None:
            return _finalize(client_mutation_id, entity, op, user, SyncMutationStatus.REJECTED,
                              error="Unknown entity '{}'".format(entity))

        required_permission = config["permissions"].get(op)
        if required_permission is None:
            return _finalize(client_mutation_id, entity, op, user, SyncMutationStatus.REJECTED,
                              error="Unsupported op '{}'".format(op))
        if not _user_has_permission(user, required_permission):
            return _finalize(client_mutation_id, entity, op, user, SyncMutationStatus.REJECTED,
                              error="Permission denied for {} {}".format(op, entity))

        try:
            with transaction.atomic():
                if op == SyncOp.CREATE:
                    obj, result_id = config["create"](user, client_id, payload)
                else:
                    target = config["model"].objects.filter(client_id=client_id).first()
                    if target and getattr(target, "deleted_at", None):
                        target = None
                    if not target:
                        raise SyncConflict("No {} found for client_id '{}'".format(entity, client_id))
                    config["check_ownership"](user, target)
                    op_fn = config["update"] if op == SyncOp.UPDATE else config["delete"]
                    obj, result_id = op_fn(user, target, payload)

                result_client_id = getattr(obj, "client_id", None) or client_id
                return _finalize(client_mutation_id, entity, op, user, SyncMutationStatus.APPLIED,
                                  result_id=result_id, result_client_id=result_client_id)
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
        try:
            return _finalize(client_mutation_id, entity, op, user, SyncMutationStatus.REJECTED, error="Unexpected error")
        except Exception:
            logger.exception("Failed to record sync ledger entry for %s", client_mutation_id)
            return _fallback_result(client_mutation_id, "Unexpected error")


def apply_mutations(user, mutations: list) -> list:
    return [apply_mutation(user, m) for m in mutations]
