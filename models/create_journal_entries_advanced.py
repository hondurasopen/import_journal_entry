# -*- encoding: utf-8 -*-
from odoo import models, fields, api,_
from odoo.exceptions import except_orm, Warning, RedirectWarning
from datetime import *


class ImportJournalEntryAdvanced(models.Model):
    _name = "import.journal.entries.advanced"
    _rec_name = "date"


    @api.depends('line_ids.debit', 'line_ids.credit')
    def _get_total_saldo(self):
        if self.line_ids:
            for importardo in self:
                for l in importardo.line_ids:
                    importardo.debit += l.debit
                    importardo.credit += l.credit


    name = fields.Char("Descripción")
    date = fields.Date("Fecha Registro", default=fields.Date.context_today)
    journal_id = fields.Many2one("account.journal", "Diario", required=True)
    line_ids = fields.One2many("journal.entries.csv.import", "parent_id", "Asientos importados")
    state = fields.Selection( [('draft', 'Borrador'), ('progress', 'Movimientos en Proceso'), ('done', 'Movimientos Validados')], string="Estado", default='draft')
    move_ids = fields.One2many("import.journal.entries.processed", "parent_id", "Asientos procesados")
    debit = fields.Float("Débitos", readonly=True, compute='_get_total_saldo', store=True)
    credit = fields.Float("Créditos", readonly=True, compute='_get_total_saldo', store=True)
    journal_entries_number = fields.Integer("Asientos generados", readonly=1)


    def unlink(self):
        for move in self:
            if not move.state == 'draft':
                raise Warning(_('No puede eliminar registros en estado procesado o validado'))
        return super(ImportJournalEntryAdvanced, self).unlink()


    def set_journal_entries_draft(self):
        for move in self.move_ids:
            move.move_id.write({'state': 'draft'})
        self.write({'state': 'progress'})


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
            self.journal_entries_number = 0

        self.write({'state': 'draft'})

 
    def valiate_journal_entries(self):
        if self.move_ids:
            for move in self.move_ids:
                move.move_id.write({'state': 'draft'})
                move.move_id.write({'state': 'posted'})
            self.write({'state': 'done'})


    def process_import_lines(self):
        if self.line_ids:
            if self.journal_id:
                for line in self.line_ids:
                    if not line.processed:
                        obj_same_line = self.env["journal.entries.csv.import"].search([('document_number', '=', line.document_number)])
                        move_obj = self.env["account.move"]
                        move_line_obj = self.env["import.journal.entries.processed"]
                        lines = []
                        for l in obj_same_line:    
                            if l.debit > 0:
                                vals = {
                                    'debit': l.debit,
                                    'credit':0.0,
                                    'amount_currency': 0.0,
                                    'name': l.ref,
                                    'account_id': l.account_id.id,
                                    'date': l.document_date,
                                }
                                lines.append((0, 0, vals))
                            if l.credit > 0:
                                vals = {
                                    'debit': 0.0,
                                    'credit': l.credit,
                                    'amount_currency': 0.0,
                                    'name': l.ref,
                                    'account_id': l.account_id.id,
                                    'date': l.document_date,
                                }
                                lines.append((0, 0, vals))
                            l.processed = True
                            self.debit += l.debit
                            self.credit += l.credit
                        vals = {
                            'journal_id': self.journal_id.id,
                            'date': line.document_date,
                            'ref': line.ref,
                            'line_ids': lines,
                            'type': 'entry',
                        }
                        id_move = move_obj.create(vals)
                        if id_move:
                            values = {
                                'parent_id': self.id,
                                'move_id': id_move.id
                            }
                            move_line_obj.create(values)
                            self.journal_entries_number += 1
                        else:
                            raise Warning(_('No se puede crear movimiento contable'))
                self.write({'state': 'progress'})
            else:
                raise Warning(_('No ha establecido las cuentas en los diarios'))


class ImportJournalEntryCSV(models.Model):
    _name = "journal.entries.csv.import"
    _rec_name = "document_number"

    parent_id = fields.Many2one("import.journal.entries.advanced", "Asientos importados")

    document_number = fields.Char("Número de documento")
    document_date = fields.Date("Fecha Documento")
    account_id = fields.Many2one("account.account", "Cuenta")
    debit = fields.Float("Débito")
    credit = fields.Float("Crédito")
    processed = fields.Boolean("Procesado", defaul=False)
    ref = fields.Char("Referencia")


class JournalEntriesProcessed(models.Model):
    _name = "import.journal.entries.processed"

    parent_id = fields.Many2one("import.journal.entries.advanced", "Asientos importados")
    move_id = fields.Many2one("account.move", "Asiento")
    state = fields.Selection([('draft', 'Borrador'), ('done', 'Hecho')], string="Estado", related="move_id.state")
    ref = fields.Char("Referencia", related="move_id.ref")