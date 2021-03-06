# -*- coding: utf-8 -*-
# This file is part of Shuup.
#
# Copyright (c) 2012-2016, Shoop Ltd. All rights reserved.
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.
import pytest

from django.conf import settings
from django.core.urlresolvers import reverse

from shuup.core.models import get_company_contact, get_person_contact
from shuup.front.apps.customer_information.notify_events import CompanyAccountCreated
from shuup.notify.actions.notification import AddNotification
from shuup.notify.models import Notification
from shuup.notify.enums import StepConditionOperator, StepNext
from shuup.notify.models import Script
from shuup.notify.script import Step
from shuup.testing.factories import get_default_shop
from shuup_tests.utils import SmartClient
from shuup_tests.utils.fixtures import (
    regular_user, REGULAR_USER_PASSWORD, REGULAR_USER_USERNAME
)



@pytest.mark.django_db
def test_notify_on_company_created(regular_user):
    if "shuup.front.apps.customer_information" not in settings.INSTALLED_APPS:
        pytest.skip("shuup.front.apps.customer_information required in installed apps")
    if "shuup.notify" not in settings.INSTALLED_APPS:
        pytest.skip("shuup.notify required in installed apps")

    step = Step(
        cond_op=StepConditionOperator.NONE,
        actions=[
            AddNotification({
                "message": {"constant": "It Works. {{ customer_email }}"},
                "message_identifier": {"constant": "company_created"},
            })
        ],
        next=StepNext.STOP
    )
    script = Script(event_identifier=CompanyAccountCreated.identifier, name="Test Script", enabled=True)
    script.set_steps([step])
    script.save()

    assert not Notification.objects.filter(identifier="company_created").exists()

    get_default_shop()
    assert get_person_contact(regular_user)
    assert not get_company_contact(regular_user)

    client = SmartClient()
    client.login(username=REGULAR_USER_USERNAME, password=REGULAR_USER_PASSWORD)
    company_edit_url = reverse("shuup:company_edit")
    client.soup(company_edit_url)

    data = _default_company_data()
    data.update(_default_address_data("billing"))
    data.update(_default_address_data("shipping"))

    response, soup = client.response_and_soup(company_edit_url, data, "post")

    assert response.status_code == 302
    assert get_company_contact(regular_user)
    assert Notification.objects.filter(identifier="company_created").count() == 1
    notification = Notification.objects.filter(identifier="company_created").first()
    assert notification
    assert data["contact-email"] in notification.message

    # New save should not add new notifications
    response, soup = client.response_and_soup(company_edit_url, data, "post")
    assert response.status_code == 302
    assert Notification.objects.filter(identifier="company_created").count() == 1
    script.delete()


def _default_company_data():
    return {
        "contact-name": "Fakerr",
        "contact-tax_number": "111110",
        "contact-phone": "11-111-111-1110",
        "contact-email": "captain@shuup.local",
    }


def _default_address_data(address_type):
    return {
        "{}-name".format(address_type) : "Fakerr",
        "{}-phone".format(address_type): "11-111-111-1110",
        "{}-email".format(address_type): "captain@shuup.local",
        "{}-street".format(address_type): "123 Fake St.",
        "{}-postal_code".format(address_type): "1234567",
        "{}-city".format(address_type): "Shuupville",
        "{}-country".format(address_type): "US",
    }
