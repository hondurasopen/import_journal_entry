# -*- encoding: utf-8 -*-
from odoo import models, fields, api,_
from odoo.exceptions import except_orm, Warning, RedirectWarning


class AccountMoveInherit(models.Model):
    _inherit = "account.move"

    verified_document = fields.Boolean("Documento Fisíco Verificado")
    document_number = fields.Char("Número de documento")

