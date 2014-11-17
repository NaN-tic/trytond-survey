#!/usr/bin/env python
# This file is part of the survey module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import ModelSingleton, ModelSQL, ModelStorage, ModelView, \
    DictSchemaMixin, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
import re
import unicodedata


__all__ = ['Configuration', 'Survey', 'SurveyField', 'View', 'Menu',
    'ActWindow', 'DynamicModel']
__metaclass__ = PoolMeta
_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_underscore_re = re.compile(r'[-\s]+')


def slugify(value):
    string = False
    if not isinstance(value, unicode):
        value = unicode(value)
        string = True
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(_slugify_strip_re.sub('', value).strip().lower())
    value = _slugify_underscore_re.sub('_', value)
    if string:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    return value


class DynamicModel(ModelStorage):
    'Dynamic Model'

    @classmethod
    def __setup__(cls):
        pool = Pool()
        if cls.module_survey_installed():
            Survey = pool.get('survey.survey')
            cursor = Transaction().cursor
            survey = Survey.__table__()
            cursor.execute(*survey.select(survey.id))
            for survey_id in cursor.fetchall():
                Class = cls.__create_class__(survey_id)
                cls.__setup_class__(Class)
            cls._fields = {}
        super(DynamicModel, cls).__setup__()

    @classmethod
    def __post_setup__(cls):
        pool = Pool()
        if cls.module_survey_installed():
            Survey = pool.get('survey.survey')
            cursor = Transaction().cursor
            survey = Survey.__table__()
            cursor.execute(*survey.select(survey.id))
            for survey_id in cursor.fetchall():
                Class = pool.get('survey.%s' % survey_id)
                cls.__post_setup_class__(Class)
        super(DynamicModel, cls).__post_setup__()

    @classmethod
    def __register__(cls, module_name):
        pool = Pool()
        if cls.module_survey_installed():
            Survey = pool.get('survey.survey')
            cursor = Transaction().cursor
            survey = Survey.__table__()
            cursor.execute(*survey.select(survey.id))
            for survey_id in cursor.fetchall():
                Class = pool.get('survey.%s' % survey_id)
                cls.__register_class__(Class, module_name)
        super(DynamicModel, cls).__register__(module_name)

    @classmethod
    def module_survey_installed(cls):
        pool = Pool()
        Module = pool.get('ir.module.module')
        return Module.search([
                ('name', '=', 'survey'),
                ('state', '=', 'installed'),
                ])

    @classmethod
    def fields_view_get(cls, view_id=None, view_type='form'):
        pool = Pool()
        View = pool.get('ir.ui.view')
        Survey = pool.get('survey.survey')

        view = View(view_id)
        Model = pool.get(view.model)
        survey = Survey(int(Model.__name__.split('.')[-1]))

        result = {}
        result['type'] = view_type
        result['view_id'] = view_id
        result['field_childs'] = None
        exclude_fields = ('id', 'create_date', 'write_date', 'create_uid',
            'write_uid')
        fields = [f for f in survey.fields_ if f not in exclude_fields]
        if view_type == 'tree':
            xml = '<tree string="%s">\n' % survey.name
            for field in fields:
                xml += '<field name="%s"/>\n' % slugify(field.string)
            xml += '</tree>\n'
            result['arch'] = xml
        elif view_type == 'form':
            xml = '<form string="%s" col="2" colspan="4">\n' % survey.name
            for field in fields:
                xml += '<label name="%s"/>\n' % slugify(field.string)
                xml += '<field name="%s"/>\n' % slugify(field.string)
            xml += '</form>\n'
            result['arch'] = xml
        else:
            assert False
        fields = [slugify(f.string) for f in fields]
        result['fields'] = Model.fields_get(fields)
        return result

    @classmethod
    def __create_class__(cls, survey_id):
        body = {
            '__doc__': 'Survey %s' % survey_id,
            '__name__': 'survey.%s' % survey_id,
            '_defaults': {},
            'fields_view_get': cls.fields_view_get,
            }
        body.update(cls.get_fields(survey_id))
        return type('survey.%s' % survey_id, (ModelSQL, ModelView), body)

    @classmethod
    def __setup_class__(cls, Class):
        'Register class an return model'
        Pool.register(Class, module='survey', type_='model')
        super(Class, Class).__setup__()

    @classmethod
    def __post_setup_class__(cls, Class):
        super(Class, Class).__post_setup__()

    @classmethod
    def __register_class__(cls, Class, module_name):
        super(Class, Class).__register__(module_name)

    @classmethod
    def get_fields(cls, survey_id):
        'Create field of new model'
        pool = Pool()
        SurveyField = pool.get('survey.field')
        Model = pool.get('ir.model')

        cursor = Transaction().cursor
        survey_field = SurveyField.__table__()
        query = survey_field.select(
                survey_field.string,
                survey_field.digits,
                survey_field.target_model,
                survey_field.type_,
                survey_field.selection,
                where=(survey_field.survey == survey_id))
        cursor.execute(*query)
        field_type = {
            'boolean': fields.Boolean,
            'integer': fields.Integer,
            'char': fields.Char,
            'date': fields.Date,
            'datetime': fields.DateTime,
            }
        result = {}
        for string, digits, target_model, type_, selection in (
                cursor.fetchall()):
            name = '%s' % slugify(string)
            if type_ in field_type:
                result[name] = field_type[type_](name)
            elif type_ == 'float':
                result[name] = fields.Float(name, digits=(16, digits))
            elif type_ == 'numeric':
                result[name] = fields.Numeric(name, digits=(16, digits))
            elif type_ == 'many2one':
                model = Model(target_model)
                result[name] = fields.Many2One(model.model, name,
                    ondelete='SET NULL')
            elif type_ == 'selection':
                selection = [[w.strip() for w in v.split(':', 1)]
                        for v in selection.splitlines() if v]
                result[name] = fields.Selection(selection, name)
        return result


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

    @classmethod
    def __setup__(cls):
        super(Survey, cls).__setup__()
        cls._buttons.update({
                'create_menus': {},
                'remove_menus': {},
                })
        cls._sql_constraints = [
            ('name_uniq', 'UNIQUE(name)',
                'name_uniq'),
            ]
        cls._error_messages.update({
                'name_uniq': 'Cannot create survey because the name must be '
                    'unique.',
                'survey_with_data': 'Survey %s has data and so cannot be '
                    'dropped.',
                })

    def create_table(self):
        transaction = Transaction()
        cursor = transaction.cursor
        field_type = {
            'boolean': 'boolean',
            'integer': 'integer',
            'char': 'character varying',
            'float': 'double precision',
            'numeric': 'numeric',
            'date': 'date',
            'datetime': 'timestamp(0) without time zone',
            'selection': 'character varying',
            'many2one': 'integer',
            }
        table_name = 'survey_%s' % self.id
        sequence_name = table_name + '_id_seq'
        sequence = ('CREATE SEQUENCE %s '
            'START WITH 1 '
            'INCREMENT BY 1 '
            'NO MINVALUE '
            'NO MAXVALUE '
            'CACHE 1;' % sequence_name)
        cursor.execute(sequence)
        query = ('CREATE TABLE %s ('
            'id integer DEFAULT nextval(\'%s\'::regclass) '
                'NOT NULL, '
            'create_date timestamp(6) without time zone, '
            'write_date timestamp(6) without time zone, '
            'create_uid integer, '
            'write_uid integer' % (table_name, sequence_name))
        for field in self.fields_:
            if field.type_ == 'one2many':
                continue
            else:
                query += ', %s %s' % (slugify(field.string),
                    field_type[field.type_])
            if field.required:
                query += ' NOT NULL'
        query += ');'
        cursor.execute(query)

    def create_action_window(self):
        ActionWindow = Pool().get('ir.action.act_window')
        action_window = ActionWindow()
        action_window.name = self.name
        action_window.res_model = 'survey.%s' % self.id
        action_window.survey = self.id
        action_window.save()
        return action_window

    def create_action_window_view(self, action, view):
        ActView = Pool().get('ir.action.act_window.view')
        act_view = ActView()
        act_view.sequence = 16
        act_view.active = True
        act_view.act_window = action.id
        act_view.view = view.id
        act_view.save()

    def create_view(self, type_):
        View = Pool().get('ir.ui.view')
        view = View()
        view.name = self.name
        view.model = 'survey.%s' % self.id
        view.module = 'survey'
        view.type = type_
        view.priority = 16
        view.survey = self.id
        view.save()
        return view

    def create_menu(self, langs):
        pool = Pool()
        Menu = pool.get('ir.ui.menu')
        ModelData = pool.get('ir.model.data')
        menu = Menu()
        menu.name = self.name
        menu.parent = Menu(ModelData.get_id('survey', 'menu_survey'))
        menu.survey = self
        menu.icon = 'tryton-list'
        menu.survey = self.id
        menu.save()

        if langs:
            for lang in langs:
                with Transaction().set_context(language=lang.code,
                        fuzzy_translation=False):
                    data, = self.read([self], fields_names=['name'])
                    Menu.write([menu], data)
        return menu

    def create_action_keyword(self, action, menu, keyword):
        ActionKeyword = Pool().get('ir.action.keyword')
        action_keyword = ActionKeyword()
        action_keyword.keyword = keyword
        action_keyword.action = action
        action_keyword.model = 'ir.ui.menu,%s' % menu.id
        action_keyword.save()
        return action_keyword

    @classmethod
    @ModelView.button
    def create_menus(cls, surveys):
        'Regenerates all actions and menu entries'
        pool = Pool()
        Lang = pool.get('ir.lang')
        langs = Lang.search([
            ('translatable', '=', True),
            ])
        cls.remove_menus(surveys)
        for survey in surveys:
            survey.create_table()

            Class = DynamicModel.__create_class__(survey.id)
            DynamicModel.__setup_class__(Class)
            DynamicModel.__post_setup_class__(Class)
            DynamicModel.__register_class__(Class, 'survey')

            action_window = survey.create_action_window()
            tree_view = survey.create_view('tree')
            form_view = survey.create_view('form')
            survey.create_action_window_view(action_window, tree_view)
            survey.create_action_window_view(action_window, form_view)
            menu = survey.create_menu(langs)
            survey.create_action_keyword(action_window.action, menu,
                'tree_open')

        return 'reload menu'

    @classmethod
    def drop_table(cls, surveys):
        cursor = Transaction().cursor
        for survey in surveys:
            table = 'survey_%s' % survey.id
            cursor.execute("DROP TABLE IF EXISTS %s " % table)
            try:
                # SQLite doesn't have sequences
                cursor.execute("DROP SEQUENCE IF EXISTS %s_id_seq" %
                    table)
            except:
                pass

    @classmethod
    @ModelView.button
    def remove_menus(cls, surveys):
        'Remove all menus and actions created'
        pool = Pool()
        ActionWindow = pool.get('ir.action.act_window')
        View = pool.get('ir.ui.view')
        Menu = pool.get('ir.ui.menu')

        action_windows = []
        views = []
        menus = []
        for survey in surveys:
            has_surveys = False
            try:
                Survey = pool.get('survey.%s' % survey.id)
                has_surveys = Survey.search([])
            except:
                cursor = Transaction().cursor
                cursor.rollback()
                continue
            if has_surveys:
                cls.raise_user_error('survey_with_data',
                    error_args=(survey.id,))
            action_windows += survey.action_windows
            views += survey.views
            menus += survey.menus
        Menu.delete(menus)
        View.delete(views)
        ActionWindow.delete(action_windows)
        cls.drop_table(surveys)
        return 'reload menu'

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
            'invisible': Eval('type_') != 'many2one',
            'required': Eval('type_') == 'many2one',
        }, depends=['type_'],
        help='Target Model.')
    target_value = fields.Integer('Value')

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
        if 'required' in cls.selection.states:
            cls.selection.states['required'] |= Eval('type_') == 'selection'
        else:
            cls.selection.states['required'] = Eval('type_') == 'selection'


class ActWindow:
    __name__ = 'ir.action.act_window'

    survey = fields.Many2One('survey.survey', 'Survey', ondelete='CASCADE')


class View:
    __name__ = 'ir.ui.view'

    survey = fields.Many2One('survey.survey', 'Survey', ondelete='CASCADE')


class Menu:
    __name__ = 'ir.ui.menu'

    survey = fields.Many2One('survey.survey', 'Survey', ondelete='CASCADE')
