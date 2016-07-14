# This file is part of Shuup.
#
# Copyright (c) 2012-2016, Shoop Ltd. All rights reserved.
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.
import pytest

from shuup.campaigns.models import CartCampaign, Coupon

from shuup.campaigns.models.cart_conditions import CartTotalProductAmountCondition, ProductsInCartCondition
from shuup.campaigns.models.cart_line_effects import FreeProductLine, DiscountFromProduct
from shuup.core.models import OrderLineType
from shuup.core.order_creator._source import LineSource
from shuup.front.cart import get_cart
from shuup.testing.factories import create_product, get_default_supplier
from shuup_tests.campaigns import initialize_test
from shuup_tests.utils import printable_gibberish


@pytest.mark.django_db
def test_cart_free_product(rf):
    request, shop, group = initialize_test(rf, False)
    price = shop.create_price

    cart = get_cart(request)
    supplier = get_default_supplier()

    single_product_price = "50"
    discount_amount_value = "10"
    original_quantity = 2
     # create cart rule that requires 2 products in cart
    product = create_product(printable_gibberish(), shop=shop, supplier=supplier, default_price=single_product_price)
    cart.add_product(supplier=supplier, shop=shop, product=product, quantity=2)
    cart.save()

    second_product = create_product(printable_gibberish(), shop=shop, supplier=supplier, default_price=single_product_price)

    rule = CartTotalProductAmountCondition.objects.create(value="2")

    campaign = CartCampaign.objects.create(active=True, shop=shop, name="test", public_name="test")
    campaign.conditions.add(rule)

    effect = FreeProductLine.objects.create(campaign=campaign, quantity=2)
    effect.products.add(second_product)

    cart.uncache()
    final_lines = cart.get_final_lines()

    assert len(final_lines) == 2

    line_types = [l.type for l in final_lines]
    assert OrderLineType.DISCOUNT not in line_types

    for line in cart.get_final_lines():
        assert line.type == OrderLineType.PRODUCT
        if line.product != product:
            assert line.product == second_product
            assert line.line_source == LineSource.DISCOUNT_MODULE
            assert line.quantity == original_quantity
        else:
            assert line.line_source == LineSource.CUSTOMER


@pytest.mark.django_db
def test_cart_free_product_coupon(rf):
    request, shop, group = initialize_test(rf, False)
    price = shop.create_price

    cart = get_cart(request)
    supplier = get_default_supplier()

    single_product_price = "50"
    discount_amount_value = "10"

     # create cart rule that requires 2 products in cart
    product = create_product(printable_gibberish(), shop=shop, supplier=supplier, default_price=single_product_price)
    cart.add_product(supplier=supplier, shop=shop, product=product, quantity=1)
    cart.add_product(supplier=supplier, shop=shop, product=product, quantity=1)
    cart.save()

    second_product = create_product(printable_gibberish(), shop=shop, supplier=supplier, default_price=single_product_price)

    rule = CartTotalProductAmountCondition.objects.create(value="2")
    coupon = Coupon.objects.create(code="TEST", active=True)

    campaign = CartCampaign.objects.create(active=True, shop=shop, name="test", public_name="test", coupon=coupon)
    campaign.conditions.add(rule)

    effect = FreeProductLine.objects.create(campaign=campaign)
    effect.products.add(second_product)

    cart.add_code(coupon.code)

    cart.uncache()
    final_lines = cart.get_final_lines()

    assert len(final_lines) == 2

    line_types = [l.type for l in final_lines]
    assert OrderLineType.DISCOUNT not in line_types

    for line in cart.get_final_lines():
        assert line.type == OrderLineType.PRODUCT

        if line.product != product:
            assert line.product == second_product


@pytest.mark.django_db
def test_productdiscountamount(rf):
    # Buy X amount of Y get Z discount from Y
    request, shop, group = initialize_test(rf, False)
    price = shop.create_price

    cart = get_cart(request)
    supplier = get_default_supplier()

    single_product_price = "50"
    discount_amount_value = "10"
    quantity = 2

     # create cart rule that requires 2 products in cart
    product = create_product(printable_gibberish(), shop=shop, supplier=supplier, default_price=single_product_price)
    cart.add_product(supplier=supplier, shop=shop, product=product, quantity=quantity)
    cart.save()

    rule = ProductsInCartCondition.objects.create(quantity=2)
    rule.products.add(product)
    rule.save()

    campaign = CartCampaign.objects.create(active=True, shop=shop, name="test", public_name="test")
    campaign.conditions.add(rule)

    effect = DiscountFromProduct.objects.create(
        campaign=campaign, discount_amount=discount_amount_value)
    effect.products.add(product)

    assert rule.matches(cart, [])
    cart.uncache()

    final_lines = cart.get_final_lines()

    assert len(final_lines) == 1  # no new lines since the effect touches original lines
    expected_discount_amount = cart.create_price(discount_amount_value)
    original_price = cart.create_price(single_product_price) * quantity
    line = final_lines[0]
    assert line.discount_amount == expected_discount_amount
    assert cart.total_price == original_price - expected_discount_amount
