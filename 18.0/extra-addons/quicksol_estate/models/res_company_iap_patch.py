from odoo import models


class ResCompanyIapPatch(models.Model):
    """Prevent partner_autocomplete from triggering IAP enrichment during seed
    data loading.

    The iap.account.get() method calls flush_all() then opens a second cursor,
    causing an internal deadlock when the main module-loading transaction holds
    exclusive locks on res_users (from DDL changes).  Skipping enrichment when
    the 'no_recompute' context flag is set (already present in company_seed.xml)
    is the minimal, non-invasive fix.
    """

    _inherit = "res.company"

    def iap_enrich_auto(self):
        if self.env.context.get("no_recompute") or self.env.context.get("tracking_disable"):
            return True
        return super().iap_enrich_auto()
