import pandas as pd
from fred import (master_data, observations, transform, chart, historical_comparison, historical_data, adder_chart,
                 category_compare,padding)
from bokeh.plotting import figure, show
from bokeh.models import NumeralTickFormatter,ColumnDataSource,HoverTool, Range1d,Panel,Tabs,Div,LinearAxis
from bokeh.layouts import layout,Spacer


PUA_url='https://oui.doleta.gov/unemploy/docs/weekly_pandemic_claims.xlsx'
pua_data=pd.read_excel(PUA_url)

y2k='2000-01-01'
cy='2020-01-01'



#Retail sales percent recovery        
retail_sales=['RSHPCS','RSGASS','RSCCAS','RSSGHBMS','RSGMS','RSMSR','RSNSR','RSFSDP','RSMVPD','RSFHFS','RSEAS','RSBMGESD','RSDBS']
retail_sales_chart=chart(retail_sales,'2019-01-01',transformation='index',transform_date='2020-02-01',titile="Change in retail sales")
for i in retail_sales_chart.legend[0]._property_values['items']:
    i._property_values['label']['value']=i._property_values['label']['value'][22:]

retail_sales=['RSHPCS','RSGASS','RSCCAS','RSSGHBMS','RSGMS','RSMSR','RSNSR','RSFSDP','RSMVPD','RSFHFS','RSEAS','RSBMGESD','RSDBS']
compare_industries=category_compare(retail_sales,'Retail Sales',nameoffset=22)

sales_charts=Panel(child=layout([
        [retail_sales_chart,compare_industries,padding()],
        
        ],sizing_mode='stretch_width'),
    title='Retail Sales')


   

#Compensation and UI change
compensation_and_ui=['W209RC1','W825RC1']
p=chart(compensation_and_ui,cy,transformation='difference',transform_date='2020-02-01')
p.renderers[0].data_source.data['difference']=p.renderers[0].data_source.data['difference']*-1
p.legend[0]._property_values['items'][0]._property_values['label']['value']='Loss in Compensation since Feb 2020'
p.legend[0]._property_values['items'][1]._property_values['label']['value']='Increase in Unemployment Insurance since Feb 2020'
p.legend.location = "top_left"
show(p)

#Personal Income and Spending
personal_income=['PI','PCE','A063RC1']
p=chart(personal_income,cy,transformation='difference',transform_date='2020-02-01')

pi=observations('PI',cy)
transfers=observations('A063RC1',cy)
tmp=pi.join(transfers,rsuffix='transfers')
tmp['value']=tmp['value']-tmp['valuetransfers']
df=transform(tmp,date='2020-02-01')
df['name']='Personal Income excluding transfers'
df['datestring']=df.date.dt.strftime("%Y-%m-%d")


p.line(x='date',y='difference', source=ColumnDataSource(df),
               legend_label='Personal Income excluding transfers',
               color='purple')
show(p)

#Manufacturing, employment, retail sales
series=['RSAFS','IPMAN','PAYEMS','DGORDER']
p=chart(series,'2019-01-01',transformation='index',transform_date='2020-02-01',title='Employment, Manufacturing, and Sales')
show(p)

#Local vs National employment
show(chart(['UNRATENSA','CASACR5URN','IURNSA','CAINSUREDUR'],'2019-01-01',title='National and Local Employment',
           offsets=[15,15,7,7]))


show(chart(['PAYEMS','CANA','SACR906NA'],'2019-01-01',
           transformation='index',
           transform_date='2020-02-01',
           title="Change in employment",
           ))

#Employment Charts
paired_series={'UNRATENSA':'CASACR5URN',
                 'IURNSA':'CAINSUREDUR',}
charts=[]
recessions=5
for i in paired_series:
    charts.append([historical_comparison(historical_data(i,recessions)),
                   historical_comparison(historical_data(paired_series[i],recessions))
                   ,Spacer(width=30, height=10, sizing_mode='fixed')])
charts[0][0].y_range=charts[0][1].y_range
charts[1][0].y_range=charts[1][1].y_range
charts.append([
                adder_chart('ICNSA',pua_data.groupby(by='Rptdate').sum()[['PUA IC']].rename(columns={'PUA IC':'value'}),recessions),
                adder_chart('CAICLAIMS',pua_data[pua_data.State=='CA'][['Rptdate','PUA IC']].rename(columns={'PUA IC':'value'}),recessions),
                Spacer(width=30, height=10, sizing_mode='fixed')
                ])
charts.append([historical_comparison(historical_data('LNU03025699',recessions)),
              historical_comparison(historical_data('UEMP15T26',recessions)),
              Spacer(width=30, height=10, sizing_mode='fixed')
    ])
show(layout(charts,sizing_mode='stretch_width'))


#Weekly Claims
recessions=5
show(layout([adder_chart('ICNSA',pua_data.groupby(by='Rptdate').sum()[['PUA IC']].rename(columns={'PUA IC':'value'}),recessions),
                adder_chart('CAICLAIMS',pua_data[pua_data.State=='CA'][['Rptdate','PUA IC']].rename(columns={'PUA IC':'value'}),recessions),
                Spacer(width=30, height=10, sizing_mode='fixed')],
       [adder_chart('CCNSA',pua_data.groupby(by='Rptdate').sum(min_count=1)[['PUA CC']].rename(columns={'PUA CC':'value'}),recessions),
                adder_chart('CACCLAIMS',pua_data[pua_data.State=='CA'][['Rptdate','PUA CC']].rename(columns={'PUA CC':'value'}),recessions),
                Spacer(width=30, height=10, sizing_mode='fixed')],sizing_mode='stretch_width'))



show(Tabs(tabs=[sales_charts]))