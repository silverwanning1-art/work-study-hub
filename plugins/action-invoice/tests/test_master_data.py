import pytest
from action_invoice.errors import NotFoundError
from action_invoice.schemas import CustomerIn, ProfileData, ProjectIn
from action_invoice.service import InvoiceService


def test_profile_is_empty_until_saved(service: InvoiceService) -> None:
    assert service.get_profile().name == ""


def test_profile_roundtrip(service: InvoiceService) -> None:
    service.save_profile(ProfileData(name="Test Person", tax_number="00/000/00000"))
    service.save_profile(ProfileData(name="Test Person 2", city="Teststadt"))

    profile = service.get_profile()

    assert (profile.name, profile.city, profile.tax_number) == ("Test Person 2", "Teststadt", "")


def test_customer_create_update_and_list(service: InvoiceService) -> None:
    created = service.save_customer(CustomerIn(name="Beispiel GmbH", city="Musterstadt"))
    service.save_customer(CustomerIn(id=created.id, name="Beispiel AG"))

    customers = service.list_customers().customers

    assert [c.name for c in customers] == ["Beispiel AG"]
    assert customers[0].city == ""


def test_update_unknown_customer_fails(service: InvoiceService) -> None:
    with pytest.raises(NotFoundError):
        service.save_customer(CustomerIn(id=99, name="X"))


def test_project_needs_existing_customer(service: InvoiceService) -> None:
    with pytest.raises(NotFoundError):
        service.save_project(ProjectIn(customer_id=1, name="Workshop"))


def test_projects_filtered_by_customer(service: InvoiceService) -> None:
    a = service.save_customer(CustomerIn(name="A"))
    b = service.save_customer(CustomerIn(name="B"))
    service.save_project(ProjectIn(customer_id=a.id, name="Workshop"))
    service.save_project(ProjectIn(customer_id=b.id, name="Konzept"))

    assert [p.name for p in service.list_projects(a.id).projects] == ["Workshop"]
    assert len(service.list_projects().projects) == 2
