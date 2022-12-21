from io import StringIO
import datetime

from rest_framework import status
from rest_framework.renderers import BaseRenderer

import pandas as pd
import numpy as np

from .models import Product, BoundaryLayer, BoundaryFeature, CropMask


class PNGRenderer(BaseRenderer):
    media_type = 'image/png'
    format = 'png'
    charset = None
    render_style = 'binary'

    def render(self, data, media_type=None, renderer_context=None):
        return data


RESPONSE_ERROR = (
    "Response data is a %s, not a DataFrame! "
    "Did you extend PandasMixin?"
)


class OldGLAMBaseZStatsRenderer(BaseRenderer):
    """
    Renders DataFrames using their built in pandas implementation.
    Only works with serializers that return DataFrames as their data object.
    Uses a StringIO to capture the output of dataframe.to_[format]()
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if renderer_context and 'response' in renderer_context:
            status_code = renderer_context['response'].status_code
            if not status.is_success(status_code):
                return "Error: %s" % data.get('detail', status_code)

        if not isinstance(data, pd.DataFrame):
            raise Exception(
                RESPONSE_ERROR % type(data).__name__
            )
        name = getattr(self, 'function', "to_%s" % self.format)
        if not hasattr(data, name):
            raise Exception("Data frame is missing %s property!" % name)

        source_url = renderer_context['view'].request.build_absolute_uri()
        params = renderer_context['kwargs']
        product_id = params['product_id']
        cropmask_id = params['cropmask_id']
        layer_id = params['layer_id']
        feature_id = params['feature_id']
        today = datetime.date.today()

        product = Product.objects.get(product_id=product_id)
        product_name = product.pt_display_name
        composite = product.composite_period - 1

        boundary_layer = BoundaryLayer.objects.get(layer_id=layer_id)
        boundary_layer_name = boundary_layer.pt_display_name

        boundary_feature = BoundaryFeature.objects.get(
            feature_id=feature_id, boundary_layer=boundary_layer)
        boundary_feature_name = boundary_feature.feature_name

        cropmask = CropMask.objects.get(cropmask_id=cropmask_id)
        cropmask_name = cropmask.pt_display_name

        data.index.name = None
        new_df = data.drop('percent_arable', 1).drop('arable_pixels', 1)
        new_df['doy'] = pd.to_datetime(
            new_df['date'], format='%Y-%m-%d').dt.dayofyear
        new_df['new_date'] = pd.to_datetime(new_df['date'])

        new_df['Start Day'] = pd.to_datetime(
            '2021'+'-'+new_df['doy'].astype(str),
            format='%Y-%j').dt.strftime('%d-%b')

        x = new_df.pivot_table(index=['doy'],
                               columns=[new_df['new_date'].dt.year],
                               values='mean_value')
        x.index.name = None

        years = x.columns.values[::-1]
        x['doy'] = x.index.values
        x['enddoy'] = [v+composite if v+composite <=
                       365 else v+composite-365 for v in x.index.values]
        start_day = pd.to_datetime(
            '2021'+'-'+x['doy'].astype(str), format='%Y-%j')
        x['Start Day'] = start_day.dt.day.astype(
            str)+'-'+start_day.dt.strftime("%b")
        end_day = pd.to_datetime(
            '2021'+'-'+x['enddoy'].astype(str), format='%Y-%j')
        x['End Day'] = end_day.dt.day.astype(str)+'-'+end_day.dt.strftime("%b")

        z = x.drop('doy', 1).drop('enddoy', 1)
        c = ['Start Day', 'End Day']
        c += [year for year in years]
        z = z[c]

        header = []
        header.insert(
            0, {'index': 'NDVI from the Global Agriculture Monitoring (GLAM) 2'})
        header.insert(1, {'index': 'Source URL', 1: source_url})
        header.insert(2, {})
        header.insert(3, {'index': 'Creation Date',
                      1: today.strftime("%Y-%m-%d")})
        header.insert(4, {})
        header.insert(5, {'index': 'Product', 1: product_name})
        header.insert(6, {'index': 'Crop Mask', 1: cropmask_name})
        header.insert(7, {'index': 'Feature ID', 1: boundary_feature_name})
        header.insert(8, {'index': 'Boundary Layer ', 1: boundary_layer_name})
        header.insert(9, {})

        header_df = pd.DataFrame(header)
        t = header_df.set_index('index')
        data = pd.concat([t, z.T])

        self.init_output()
        args = self.get_pandas_args(data)
        kwargs = self.get_pandas_kwargs(data, renderer_context)

        self.render_dataframe(data, name, *args, **kwargs)
        return self.get_output()

    def render_dataframe(self, data, name, *args, **kwargs):
        function = getattr(data, name)
        function(*args, **kwargs, sep='\t', header=False)

    def init_output(self):
        self.output = StringIO()

    def get_output(self):
        return self.output.getvalue()

    def get_pandas_args(self, data):
        return [self.output]

    def get_pandas_kwargs(self, data, renderer_context):
        return {}


class OldGLAMZStatsRenderer(OldGLAMBaseZStatsRenderer):
    """
    Renders data frame as CSV, but uses text/plain as media type
    """
    media_type = "text/plain"
    format = "oldglam"
    function = "to_csv"
    sep = "tab"


class OldGLAMBaseHistRenderer(BaseRenderer):
    """
    Renders DataFrames using their built in pandas implementation.
    Only works with serializers that return DataFrames as their data object.
    Uses a StringIO to capture the output of dataframe.to_[format]()
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if renderer_context and 'response' in renderer_context:
            status_code = renderer_context['response'].status_code
            if not status.is_success(status_code):
                return "Error: %s" % data.get('detail', status_code)

        if not isinstance(data, pd.DataFrame):
            raise Exception(
                RESPONSE_ERROR % type(data).__name__
            )

        name = getattr(self, 'function', "to_%s" % self.format)
        if not hasattr(data, name):
            raise Exception("Data frame is missing %s property!" % name)

        source_url = renderer_context['view'].request.build_absolute_uri()

        if renderer_context['request'].method == 'POST':
            params = renderer_context['request'].data
        else:
            params = renderer_context['kwargs']
            layer_id = params['layer_id']
            feature_id = params['feature_id']
            boundary_layer = BoundaryLayer.objects.get(layer_id=layer_id)
            boundary_layer_name = boundary_layer.pt_display_name
            boundary_feature = BoundaryFeature.objects.get(
                feature_id=feature_id, boundary_layer=boundary_layer)
            boundary_feature_name = boundary_feature.feature_name

        product_id = params['product_id']
        cropmask_id = params['cropmask_id']
        date = params['date']
        today = datetime.date.today()

        product = Product.objects.get(product_id=product_id)
        product_name = product.pt_display_name

        cropmask = CropMask.objects.get(cropmask_id=cropmask_id)
        cropmask_name = cropmask.pt_display_name

        bins = data.iloc[0]
        bin_edges = bins['bin_edges']
        series = np.round(pd.Series(bin_edges), 4)
        bin_series = series.to_frame().T

        new_df = []
        for index, row in data.iterrows():
            hist_values = row['hist']
            # add leading 0 to match bins
            hist_values = np.insert(hist_values, 0, [0])
            hist_series = pd.Series(hist_values).to_frame().T
            new_df.append(hist_series)

        df = pd.concat(new_df)

        df['total'] = df.sum(axis=1).values
        df_new = df.loc[:].div(df["total"], axis=0).multiply(100)
        df_new = pd.concat([bin_series, df_new.round(4)])
        dates = data['date'].values
        new_dates = ['Name']
        for date in dates:
            new_dates.append(datetime.datetime.strptime(
                date, '%Y-%d-%m').strftime('%Y-%b-%d'))
        new_dates = np.array(new_dates)

        df_new.insert(loc=0, column='index', value=new_dates)
        df_new = df_new.drop('total', axis=1)
        df_new = df_new.set_index('index')

        header = []
        header.insert(
            0, {'index': 'NDVI from the Global Agriculture Monitoring (GLAM) 2'})
        header.insert(1, {'index': 'Source URL', 0: source_url})
        header.insert(2, {})
        header.insert(3, {'index': 'Creation Date',
                      0: today.strftime("%Y-%m-%d")})
        header.insert(4, {})
        header.insert(5, {'index': 'Product', 1: product_name})
        header.insert(6, {'index': 'Crop Mask', 1: cropmask_name})
        if renderer_context['request'].method == 'POST':
            header.insert(7, {'index': 'Feature ID', 1: 'Custom Geometry'})
            header.insert(
                8, {'index': 'Boundary Layer ', 1: 'Custom Geometry'})
        else:
            header.insert(7, {'index': 'Feature ID', 1: boundary_feature_name})
            header.insert(
                8, {'index': 'Boundary Layer ', 1: boundary_layer_name})
        header.insert(9, {})

        header_df = pd.DataFrame(header)
        t = header_df.set_index('index')
        data = pd.concat([t, df_new])

        self.init_output()
        args = self.get_pandas_args(data)
        kwargs = self.get_pandas_kwargs(data, renderer_context)

        self.render_dataframe(data, name, *args, **kwargs)
        return self.get_output()

    def render_dataframe(self, data, name, *args, **kwargs):
        function = getattr(data, name)
        function(*args, **kwargs, sep='\t', header=False)

    def init_output(self):
        self.output = StringIO()

    def get_output(self):
        return self.output.getvalue()

    def get_pandas_args(self, data):
        return [self.output]

    def get_pandas_kwargs(self, data, renderer_context):
        return {}


class OldGLAMHistRenderer(OldGLAMBaseHistRenderer):
    """
    Renders data frame as CSV, but uses text/plain as media type
    """
    media_type = "text/plain"
    format = "oldglam"
    function = "to_csv"
    sep = "tab"
