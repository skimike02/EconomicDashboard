# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 10:25:59 2020

@author: Micha
"""

import pandas as pd
from fred import (master_data, observations, transform, chart, bar_chart, historical_comparison, historical_data, adder_chart,
                 category_compare,padding)
from bokeh.plotting import figure, show, save
from bokeh.models import NumeralTickFormatter,ColumnDataSource,HoverTool, Range1d,Panel,Tabs,Div,LinearAxis
from bokeh.layouts import layout,Spacer

PUA_url='https://oui.doleta.gov/unemploy/docs/weekly_pandemic_claims.xlsx'
pua_data=pd.read_excel(PUA_url)
fileloc="C:\\Users\\Micha\\Documents\\GitHub\\EconomicDashboard"

y2k='2000-01-01'
cy='2020-01-01'

#Weekly Claims
recessions=5
national_initial_claims=adder_chart('ICNSA',pua_data.groupby(by='Rptdate').sum()[['PUA IC']].rename(columns={'PUA IC':'value'}),recessions,years=3)
ca_initial_claims=adder_chart('CAICLAIMS',pua_data[pua_data.State=='CA'][['Rptdate','PUA IC']].rename(columns={'PUA IC':'value'}),recessions,years=3)
national_continuing_claims=adder_chart('CCNSA',pua_data.groupby(by='Rptdate').sum(min_count=1)[['PUA CC']].rename(columns={'PUA CC':'value'}),recessions,years=3)
ca_continuing_claims=adder_chart('CACCLAIMS',pua_data[pua_data.State=='CA'][['Rptdate','PUA CC']].rename(columns={'PUA CC':'value'}),recessions,years=3)

weekly_claims=Panel(child=layout([
    [national_initial_claims,ca_initial_claims,padding()],
    [national_continuing_claims,ca_continuing_claims,padding()]
    ],
    sizing_mode='stretch_width'),
    title="Weekly Claims")

#Overall Trends
series=['RSAFS','IPMAN','PAYEMS','DGORDER']
national_trends=chart(series,'2019-01-01',transformation='index',transform_date='2020-02-01',title='Employment, Manufacturing, and Sales')
overall_trends=Panel(child=layout([
    [national_trends,padding()]
    ],
    sizing_mode='stretch_width'),
    title='Overall Trends')

#ADP Charts
adp_sectors=['NPPSPT','NPPGPT']
adp_sectors=['NPPMNF','NPPCON','NPPTTU','NPPBUS','NPPFIN']
adp_sizes=['NPPTS1','NPPTS2','NPPTM','NPPTL1','NPPTL2']

sector_index=chart(adp_sectors,cy,transformation='index',transform_date='2020-02-01',title='National Nonfarm Private Payroll for Select Sectors (ADP)',lstrip=16,rstrip=19)
sector_index_bar=bar_chart(adp_sectors,cy,title='National Nonfarm Private Payroll for Select Sectors (ADP)',lstrip=16,rstrip=19)
sector_difference_bar=bar_chart(adp_sectors,cy,transformation='difference',transform_date='2020-02-01',title='National Nonfarm Private Payroll for Select Sectors (ADP)',lstrip=16,rstrip=19)
size_index=chart(adp_sizes,cy,transformation='index',transform_date='2020-02-01',title='National Nonfarm Private Payroll by Business Size (ADP)',lstrip=16)
size_index_bar=bar_chart(adp_sizes,cy,title='National Nonfarm Private Payroll by Business Size (ADP)',lstrip=16)
size_difference_bar=bar_chart(adp_sizes,cy,transformation='difference',transform_date='2020-02-01',title='National Nonfarm Private Payroll by Business Size (ADP)',lstrip=16)
copyright_note=Div(text="<p>Copyright Automatic Data Processing, Inc. Retrieved from FRED, Federal Reserve Bank of St. Louis</p>")

ADP=Panel(child=layout([
    [sector_index,size_index,padding()],
    [sector_index_bar,size_index_bar,padding()],
    [sector_difference_bar,size_difference_bar,padding()],
    [copyright_note]
    ],
    sizing_mode='stretch_width'),
    title='ADP Monthly Data')


#Retail sales percent recovery        
retail_sales=['RSHPCS','RSGASS','RSCCAS','RSSGHBMS','RSGMS','RSMSR','RSNSR','RSFSDP','RSMVPD','RSFHFS','RSEAS','RSBMGESD','RSDBS']
retail_sales_chart=chart(retail_sales,'2019-01-01',transformation='index',transform_date='2020-02-01',title="Change in retail sales")
for i in retail_sales_chart.legend[0]._property_values['items']:
    i._property_values['label']['value']=i._property_values['label']['value'][22:]

retail_sales=['RSHPCS','RSGASS','RSCCAS','RSSGHBMS','RSGMS','RSMSR','RSNSR','RSFSDP','RSMVPD','RSFHFS','RSEAS','RSBMGESD','RSDBS']
compare_industries=category_compare(retail_sales,'Retail Sales',nameoffset=22)

sales_charts=Panel(child=layout([
        [retail_sales_chart,compare_industries,padding()],
        
        ],sizing_mode='stretch_width'),
    title='Retail Sales')



#About
about_html="""
<p><b>Data Sources and Documentation</b></p>
<p>Data from <a href="https://fred.stlouisfed.org/docs/api/fred/">FRED® API</a> unless otherwise noted below. This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.</p>
<p>PUA data pulled from the <a href="https://oui.doleta.gov/unemploy/docs/weekly_pandemic_claims.xlsx">US Department of Labor</a></p>
<p>Business Pulse Survey Data pulled from <a href="https://www.census.gov/data/experimental-data-products/small-business-pulse-survey.html">US Census Bureau</a></p>
<p>Household Pulse Survey Data pulled from <a href="https://www.census.gov/programs-surveys/household-pulse-survey/data.html">US Census Bureau</a></p>
"""
about=Panel(child=Div(text=about_html),title='About')

#page=Tabs(tabs=[overall_trends,weekly_claims,sales_charts,ADP])
page=Tabs(tabs=[overall_trends])
show(page)

save(page,resources=None,filename=fileloc+'EconomicIndicators.html',title='Economic Dashboard')



"""

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


show(Tabs(tabs=[sales_charts]))

"""