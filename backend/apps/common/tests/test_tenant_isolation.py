from django.test import SimpleTestCase


class TenantIsolationDesignTest(SimpleTestCase):
    """
    Basic structural test for the tenant-isolation foundation.
    """

    def test_common_tenant_mixin_module_exists(self):
        from apps.common.mixins import OrganizationQuerysetMixin

        self.assertTrue(
            OrganizationQuerysetMixin
        )