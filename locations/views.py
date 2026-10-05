from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from accounts.models import UserRole
from dashboard.access import role_required

from .forms import (
    DistrictForm,
    DistrictOfficerAssignmentForm,
    DivisionalSecretariatForm,
    GNDivisionForm,
    ProvinceForm,
)
from .models import (
    District,
    DistrictOfficerAssignment,
    DivisionalSecretariat,
    GNDivision,
    Province,
)


location_admin_required = role_required(
    UserRole.PLATFORM_ADMIN,
    UserRole.SUPER_ADMIN,
)


ENTITY_CONFIG = {
    "provinces": {
        "model": Province,
        "form": ProvinceForm,
        "title": _("Provinces"),
        "singular": _("Province"),
        "select_related": (),
    },
    "districts": {
        "model": District,
        "form": DistrictForm,
        "title": _("Districts"),
        "singular": _("District"),
        "select_related": ("province",),
    },
    "ds-divisions": {
        "model": DivisionalSecretariat,
        "form": DivisionalSecretariatForm,
        "title": _("Divisional Secretariats"),
        "singular": _("Divisional Secretariat"),
        "select_related": ("district", "district__province"),
    },
    "gn-divisions": {
        "model": GNDivision,
        "form": GNDivisionForm,
        "title": _("GN Divisions"),
        "singular": _("GN Division"),
        "select_related": (
            "divisional_secretariat",
            "divisional_secretariat__district",
        ),
    },
}


def _get_config(entity):
    try:
        return ENTITY_CONFIG[entity]
    except KeyError as exc:
        raise Http404("Unknown location entity.") from exc


def _search_queryset(entity, queryset, query):
    if not query:
        return queryset

    common = (
        Q(code__icontains=query)
        | Q(name_en__icontains=query)
        | Q(name_ta__icontains=query)
        | Q(name_ar__icontains=query)
    )

    if entity == "districts":
        common |= Q(province__name_en__icontains=query)
    elif entity == "ds-divisions":
        common |= Q(district__name_en__icontains=query)
    elif entity == "gn-divisions":
        common |= (
            Q(divisional_secretariat__name_en__icontains=query)
            | Q(divisional_secretariat__district__name_en__icontains=query)
        )

    return queryset.filter(common)


@location_admin_required
def location_management(request):
    context = {
        "province_count": Province.objects.count(),
        "district_count": District.objects.count(),
        "ds_count": DivisionalSecretariat.objects.count(),
        "gn_count": GNDivision.objects.count(),
        "assignment_count": DistrictOfficerAssignment.objects.filter(
            is_active=True
        ).count(),
    }
    return render(request, "locations/management.html", context)


@location_admin_required
def location_list(request, entity):
    config = _get_config(entity)
    queryset = config["model"].objects.all()
    if config["select_related"]:
        queryset = queryset.select_related(*config["select_related"])

    query = request.GET.get("q", "").strip()
    queryset = _search_queryset(entity, queryset, query)

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "locations/location_list.html",
        {
            "entity": entity,
            "title": config["title"],
            "singular": config["singular"],
            "page_obj": page_obj,
            "query": query,
        },
    )


@location_admin_required
def location_form(request, entity, pk=None):
    config = _get_config(entity)
    instance = None
    if pk is not None:
        instance = get_object_or_404(config["model"], pk=pk)

    form = config["form"](request.POST or None, instance=instance)

    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(
            request,
            _("%(name)s saved successfully.") % {"name": obj},
        )
        return redirect("locations:list", entity=entity)

    return render(
        request,
        "locations/location_form.html",
        {
            "form": form,
            "entity": entity,
            "title": config["singular"],
            "is_edit": instance is not None,
        },
    )


@location_admin_required
def location_delete(request, entity, pk):
    config = _get_config(entity)
    obj = get_object_or_404(config["model"], pk=pk)

    if request.method == "POST":
        try:
            obj.delete()
            messages.success(request, _("Location record deleted successfully."))
        except Exception:
            messages.error(
                request,
                _("This record cannot be deleted because other records depend on it. Deactivate it instead."),
            )
        return redirect("locations:list", entity=entity)

    return render(
        request,
        "locations/location_confirm_delete.html",
        {
            "object": obj,
            "entity": entity,
            "title": config["singular"],
        },
    )


@location_admin_required
def officer_assignment_list(request):
    assignments = DistrictOfficerAssignment.objects.select_related(
        "user",
        "district",
        "district__province",
    )
    return render(
        request,
        "locations/officer_assignment_list.html",
        {"assignments": assignments},
    )


@location_admin_required
def officer_assignment_form(request, pk=None):
    instance = None
    if pk is not None:
        instance = get_object_or_404(DistrictOfficerAssignment, pk=pk)

    form = DistrictOfficerAssignmentForm(
        request.POST or None,
        instance=instance,
    )

    if request.method == "POST" and form.is_valid():
        assignment = form.save()
        messages.success(
            request,
            _("District officer assignment saved for %(user)s.")
            % {"user": assignment.user},
        )
        return redirect("locations:officer_assignments")

    return render(
        request,
        "locations/officer_assignment_form.html",
        {
            "form": form,
            "is_edit": instance is not None,
        },
    )


@location_admin_required
def officer_assignment_delete(request, pk):
    assignment = get_object_or_404(DistrictOfficerAssignment, pk=pk)

    if request.method == "POST":
        assignment.delete()
        messages.success(request, _("District officer assignment removed."))
        return redirect("locations:officer_assignments")

    return render(
        request,
        "locations/officer_assignment_confirm_delete.html",
        {"assignment": assignment},
    )


def api_districts(request):
    province_id = request.GET.get("province")
    queryset = District.objects.filter(is_active=True)
    if province_id:
        queryset = queryset.filter(province_id=province_id)
    else:
        queryset = queryset.none()

    return JsonResponse(
        {
            "results": [
                {"id": obj.id, "text": obj.get_localized_name()}
                for obj in queryset.order_by("name_en")
            ]
        }
    )


def api_ds_divisions(request):
    district_id = request.GET.get("district")
    queryset = DivisionalSecretariat.objects.filter(is_active=True)
    if district_id:
        queryset = queryset.filter(district_id=district_id)
    else:
        queryset = queryset.none()

    return JsonResponse(
        {
            "results": [
                {"id": obj.id, "text": obj.get_localized_name()}
                for obj in queryset.order_by("name_en")
            ]
        }
    )


def api_gn_divisions(request):
    ds_id = request.GET.get("ds")
    queryset = GNDivision.objects.filter(is_active=True)
    if ds_id:
        queryset = queryset.filter(divisional_secretariat_id=ds_id)
    else:
        queryset = queryset.none()

    return JsonResponse(
        {
            "results": [
                {"id": obj.id, "text": obj.get_localized_name()}
                for obj in queryset.order_by("name_en")
            ]
        }
    )
