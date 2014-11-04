#!/usr/bin/env python
# This file is part of the survey module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import ModelSingleton, ModelSQL, ModelView, DictSchemaMixin, fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval, Bool

__all__ = ['Configuration', 'Survey', 'SurveyField']
__metaclass__ = PoolMeta


class Configuration(ModelSingleton, ModelSQL, ModelView):
    'Survey Configuration'
    __name__ = 'survey.configuration'


class Survey(ModelSQL, ModelView):
    'Survey'
    __name__ = 'survey.survey'
    name = fields.Char('Name', required=True, translate=True)
    code = fields.Char('Code')
    fields_ = fields.One2Many('survey.field', 'survey', 'Fields')

    def get_rec_name(self, name):
        if self.code:
            return '[' + self.code + '] ' + self.name
        else:
            return self.name

    def save_data(self, survey, data):
        '''Get values from a survey
        :param survey: obj
        :param data: dict
        '''
        return True


class SurveyField(DictSchemaMixin, ModelSQL, ModelView):
    "Survey Field"
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
        help="Text multiple lines")

    @staticmethod
    def default_sequence():
        return 1

    @classmethod
    def __setup__(cls):
        super(SurveyField, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))