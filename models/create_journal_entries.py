# -*- encoding: utf-8 -*-
from odoo import models, fields, api,_
from odoo.exceptions import except_orm, Warning, RedirectWarning


class ImportJournalEntry(models.Model):
    _name = "import.journal.entries"

    name = fields.Char("Descripción")
    journal_id = fields.Many2one("account.journal", "Diario", required=True)
    line_ids = fields.One2many("import.journal.entries.detail", "parent_id", "Detalle")
    state = fields.Selection( [('draft', 'Borrador'), ('progress', 'Movimientos en Proceso'), ('done', 'Realizado')], string="Estado", default='draft')
    move_ids = fields.One2many("import.journal.entries.created", "parent_id", "Detalle de asientos")
    debit = fields.Float("Débitos", readonly=True)
    credit = fields.Float("Créditos", readonly=True)

    @api.multi
    def unlink(self):
        for move in self:
            if not move.state == 'draft':
                raise Warning(_('No puede eliminar registros en estado procesado o validado'))
        return super(ImportJournalEntry, self).unlink()


    @api.multi
    def set_journal_entries_draft(self):
        for move in self.move_ids:
            move.move_id.write({'state': 'draft'})
        self.write({'state': 'progress'})

    @api.multi
    def delete_journal_entries(self):
        if self.move_ids:
            for l in self.move_ids:
                l.move_id.write({'state': 'draft'})
                l.move_id.unlink()
                l.unlink()
            for l in self.line_ids:
                l.processed = False
            self.debit = 0
            self.credit = 0

        self.write({'state': 'draft'})


    @api.multi
    def valiate_journal_entries(self):
        if self.move_ids:
            for move in self.move_ids:
                move.move_id.write({'state': 'draft'})
                move.move_id.write({'state': 'posted'})
                move.move_id.write({'name': str(move.document_number)})
            self.write({'state': 'done'})


    @api.multi
    def process_import_lines(self):
        if self.line_ids:
            if self.journal_id:
                for line in self.line_ids:
                    if line.is_ok and  not line.processed:
                        self.debit += line.debit
                        self.credit += line.credit
                        move_obj = self.env["account.move"]
                        move_line_obj = self.env["import.journal.entries.created"]
                        lines = []
                        account_id = False
                        if line.debit > 0:
                            vals = {
                                'debit': line.debit,
                                'credit':0.0,
                                'amount_currency': 0.0,
                                'name': line.description,
                                'account_id': line.account_id.id,
                                'date': line.document_date,
                            }
                            lines.append((0, 0, vals))
                            account_id = self.journal_id.default_credit_account_id.id
                            
                        if line.credit > 0:
                            vals = {
                                'debit': 0.0,
                                'credit': line.credit,
                                'amount_currency': 0.0,
                                'name': line.description,
                                'account_id': line.account_id.id,
                                'date': line.document_date,
                            }
                            lines.append((0, 0, vals))
                            account_id = self.journal_id.default_debit_account_id.id
                        values = {
                                'debit': line.credit, 
                                'credit': line.debit,
                                'amount_currency': 0.0,
                                'name': line.description,
                                'account_id': account_id,
                                'date': line.document_date,
                            }
                        lines.append((0, 0, values))
                        vals = {
                            'journal_id': self.journal_id.id,
                            'date': line.document_date,
                            'ref': line.description + " - " + line.bank_transaction,
                            'narration': line.description,
                            'line_ids': lines,
                        }
                        id_move = move_obj.create(vals)
                        if id_move:
                            values = {
                                'parent_id': self.id,
                                'move_id': id_move.id
                            }
                            move_line_obj.create(values)
                            line.processed = True
                            if line.verified_document:
                                id_move.verified_document = True
                                id_move.document_number = line.document_number

                self.write({'state': 'progress'})
            else:
                raise Warning(_('No ha establecido las cuentas en los diarios'))



class ImportJournalEntryLine(models.Model):
    _name = "import.journal.entries.detail"
    _rec_name = "document_number"


    parent_id = fields.Many2one("import.journal.entries", "Asiento importado")

    document_number = fields.Char("Número de documento")
    document_date = fields.Date("Fecha Documento")
    account_id = fields.Many2one("account.account", "Cuenta")
    debit = fields.Float("Débito")
    credit = fields.Float("Crédito")
    processed = fields.Boolean("Procesado", defaul=False)
    is_ok = fields.Boolean("Linea Correcta", defaul=False)
    verified_document = fields.Char("Documento Fisíco")
    bank_transaction = fields.Char("Transacción Banco")
    description = fields.Char("Descripción")
    beneficiary = fields.Char("Beneficiario")



class JournalEntriesCreated(models.Model):
    _name = "import.journal.entries.created"

    parent_id = fields.Many2one("import.journal.entries", "Asiento importado")
    move_id = fields.Many2one("account.move", "Asiento")
    state = fields.Selection([('draft', 'Borrador'), ('done', 'Hecho')], string="Estado", related="move_id.state")
    ref = fields.Char("Referencia", related="move_id.ref")
    verified_document = fields.Boolean("Documento fisico verificado", related="move_id.verified_document")
    narration = fields.Text("Descripción", related="move_id.narration")
    document_number = fields.Char("Número de documento", related="move_id.document_number")