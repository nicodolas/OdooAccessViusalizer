from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        return ["odoo_access_visualizer", *super()._get_translation_frontend_modules_name()]
