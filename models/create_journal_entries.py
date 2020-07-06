# -*- encoding: utf-8 -*-
from odoo import models, fields, api,_
from odoo.exceptions import except_orm, Warning, RedirectWarning


class ImportJournalEntry(models.Model):
    _name = "import.journal.entries"

    name = fields.Char("Descripción")
    journal_id = fields.Many2one("account.journal", "Diario", required=True)
    line_ids = fields.One2many("import.journal.entries.detail", "parent_id", "Line")
    state = fields.Selection( [('draft', 'Borrador'), ('done', 'Hecho')], string="Estado", default='draft')
    move_ids = fields.One2many("import.journal.entries.created", "parent_id", "Detalle de asientos")


    @api.multi
    def process_import_lines(self):
        if self.line_ids:
            if self.journal_id:
                for line in self.line_ids:
                    obj_move = self.env["account.move"]
                    vals_bank = {
                        'debit': 0.0,
                        'credit': self.net_total,
                        'amount_currency': 0.0,
                        'name': 'Sueldos y Salarios',
                        'account_id': self.journal_id.default_debit_account_id.id,
                            'date': self.end_date,
                    }



class ImportJournalEntryLine(models.Model):
    _name = "import.journal.entries.detail"

    parent_id = fields.Many2one("import.journal.entries", "Asiento importado")

    name = fields.Char("Número de documento")
    document_date = fields.Date("Fecha Documento")
    account_id = fields.Many2one("account.account", "Cuenta")
    debit = fields.Float("Débito")
    credit = fields.Float("Crédito")
    processed = fields.Boolean("Procesado", defaul=False)
    verified_document = fields.Char("Documento Fisíco")
    bank_transaction = fields.Char("Transacción Banco")
    description = fields.Char("Descripción")
    beneficiary = fields.Char("Beneficiario")


class JournalEntriesCreated(models.Model):
    _name = "import.journal.entries.created"

    parent_id = fields.Many2one("import.journal.entries", "Asiento importado")
    move_id = fields.Many2one("account.move", "Asiento")
    state = fields.Selection([('draft', 'Borrador'), ('done', 'Hecho')], string="Estado")