#!/usr/bin/env python
# This file is part of the survey module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import ModelSingleton, ModelSQL, ModelView, \
    DictSchemaMixin, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, In, Not


__all__ = ['Configuration', 'Survey', 'SurveyField', 'View', 'Menu',
    'ActWindow']
__metaclass__ = PoolMeta


class Configuration(ModelSingleton, ModelSQL, ModelView):
    'Survey Configuration'
    __name__ = 'survey.configuration'


class Survey(ModelSQL, ModelView):
    'Survey'
    __name__ = 'survey.survey'
    name = fields.Char('Name', required=True, translate=True)
    code = fields.Char('Code')
    active = fields.Boolean('Active')
    fields_ = fields.One2Many('survey.field', 'survey', 'Fields')
    menus = fields.One2Many('ir.ui.menu', 'survey', 'Menus',
        readonly=True)
    action_windows = fields.One2Many('ir.action.act_window', 'survey',
        'Actions', readonly=True)
    views = fields.One2Many('ir.ui.view', 'survey', 'Views',
        readonly=True)

    @staticmethod
    def default_active():
        return True

    def get_rec_name(self, name):
        if self.code:
            return '[' + self.code + '] ' + self.name
        else:
            return self.name

    @classmethod
    def save_data(cls, survey, data):
        '''Get values from a survey
        :param survey: obj
        :param data: dict
        '''
        return True


class SurveyField(DictSchemaMixin, ModelSQL, ModelView):
    'Survey Field'
    __name__ = 'survey.field'
    _rec_name = 'sequence'
    survey = fields.Many2One('survey.survey', 'Survey', ondelete='CASCADE',
        select=True)
    sequence = fields.Integer('Sequence')
    required = fields.Boolean('Required')
    help_ = fields.Char('Help', translate=True)
    textarea = fields.Boolean('Textarea',
        states={
            'invisible': Eval('type_') != 'char',
        }, depends=['type_'],
        help='Text multiple lines')
    email = fields.Boolean('Email',
        states={
            'invisible': Eval('type_') != 'char',
        }, depends=['type_'],
        help='Text email field')
    url = fields.Boolean('URL',
        states={
            'invisible': Eval('type_') != 'char',
        }, depends=['type_'],
        help='Text URL field')
    default_value = fields.Char('Default',
        help='Default value in field')
    password = fields.Boolean('Password',
        states={
            'invisible': Eval('type_') != 'char',
        }, depends=['type_'],
        help="Text password field")

    target_model = fields.Many2One('ir.model', 'Model',
        states={
            'invisible': Not(In(Eval('type_'), ['many2one', 'one2many']))
        }, depends=['type_'],
        help='Target Model.')
    target_value = fields.Integer('Value')
    target_values = fields.Char('Values')

    @staticmethod
    def default_sequence():
        return 1

    @classmethod
    def __setup__(cls):
        super(SurveyField, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))
        selection = ('many2one', 'Many2One')
        if selection not in cls.type_.selection:
            cls.type_.selection.append(selection)
        selection = ('one2many', 'One2Many')
        if selection not in cls.type_.selection:
            cls.type_.selection.append(selection)


class ActWindow:
    __name__ = 'ir.action.act_window'

    survey = fields.Many2One('survey.survey', 'Survey')


class View:
    __name__ = 'ir.ui.view'

    survey = fields.Many2One('survey.survey', 'Survey')


class Menu:
    __name__ = 'ir.ui.menu'

    survey = fields.Many2One('survey.survey', 'Survey')
