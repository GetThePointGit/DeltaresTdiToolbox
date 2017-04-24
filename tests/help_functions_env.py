import os.path

import numpy as np

import ThreeDiToolbox.datasource.netcdf
reload(ThreeDiToolbox.datasource.netcdf)

NetcdfDataSource = ThreeDiToolbox.datasource.netcdf.NetcdfDataSource

test_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)))
model_dir = os.path.join(test_dir, 'bigdata', 'vecht_rekenen_tekenen_demo')
nc_file = os.path.join(model_dir, 'vecht_s2_scenario', 'results', 'subgrid_map.nc')

links = {}
links['2d_in'] = [2253, 2254, 2255, 2256, 9610]
links['2d_out'] = [2265, 2266, 2267, 2268, 12861]

tnp_link = [[],[],[]]

for l in links['2d_in']:
    tnp_link[0].append(l)
    tnp_link[1].append(2)
    tnp_link[2].append(1)

for l in links['2d_out']:
    tnp_link[0].append(l)
    tnp_link[1].append(2)
    tnp_link[2].append(-1)

np_link = np.array(tnp_link)
# np_link = np_link.transpose()

nc = NetcdfDataSource(nc_file)

pos = np.zeros(shape=(len(np_link[0])))
neg = np.zeros(shape=(len(np_link[0])))

ts = nc.timesteps
for ts_idx, dt in enumerate(ts):

    vol = nc.get_values_by_timestep_nr('q', ts_idx, np_link[0]) * np_link[2] * dt

    pos += vol.clip(min=0)
    neg += vol.clip(max=0)

print pos.sum()
print neg.sum()
print pos.sum() + neg.sum()
