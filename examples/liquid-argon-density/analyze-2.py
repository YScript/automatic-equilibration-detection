#!/usr/bin/env python

"""
Analyze multiple replicates of a simulation of liquid argon at constant pressure.

"""

import numpy as np
import os.path
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import pylab
#import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import netCDF4

#from equilibration import statisticalInefficiency_geyer as statisticalInefficiency
from equilibration import statisticalInefficiency_multiscale as statisticalInefficiency

netcdf_filename = 'data.nc'
figure_directory = 'figures'

t0max = 1001 # largest number of initial samples to discard
tmax = 2000 # total trajectory length to include in analysis

#
# Ensure figure directory exists
#

if not os.path.exists(figure_directory):
    print "Creating figures directory..."
    os.makedirs(figure_directory)
#
# READ DATA
#

# Open NetCDF file
ncfile = netCDF4.Dataset(netcdf_filename, 'r')
[nreplicates, niterations] = ncfile.variables['reduced_density'].shape
observation_interval = ncfile.variables['observation_interval'].getValue() # ps
ps_per_iteration = observation_interval

# Select data to analyze.
A_it = np.array(ncfile.variables['reduced_density'][:,:], np.float64)

# Compute true expectation using mean of second half of all simulations.
t0 = int(niterations/2)
true_expectation = A_it[:,t0:].mean(1).mean(0)

# Compute true expectation using all data. # DEBUG
#true_expectation = A_it.mean().mean()
#print "true expectation (from all data) : %f" % true_expectation

#
# BIAS-VARIANCE TRADEOFF CALCULATIONS
#

x = np.arange(niterations+1) * ps_per_iteration # ps
A_t = A_it.mean(0)
dA_t = A_it.std(0)

# Compute integrated autocorrelation times.
print "Computing integrated autocorrelation times for all initial equilibration times t0..."
g_it = np.zeros([nreplicates,t0max], np.float64)
for replicate in range(nreplicates):
    print "replicate %d / %d..." % (replicate, nreplicates)
    for t0 in range(t0max):
        A_t = np.squeeze(A_it[replicate, t0:tmax])
        g_it[replicate,t0] = statisticalInefficiency(A_t)

# Compute effective number of uncorrelated samples.
print "Computing effective number of uncorrelated samples..."
N_it = np.zeros([nreplicates,t0max], np.float64)
for replicate in range(nreplicates):
    print "replicate %d / %d..." % (replicate, nreplicates)
    for t0 in range(t0max):
        N_it[replicate,t0] = (tmax-t0+1) / g_it[replicate,t0]

# Determine optimal equilibration end (t0equil) by maximum number of effective samples (max of Neff).
t0equil = np.argmax(N_it.mean(0))
print "t0equil = %d" % t0equil

# Determine individual t0equil points.
print "Determining optimal equilibration times for each trajectory..."
t0equil_i = np.zeros([nreplicates], np.int32)
for replicate in range(nreplicates):
    t0equil_i[replicate] = np.argmax(N_it[replicate,:])

# Determine mean as a function of initial t0.
tbvmax = tmax - 200
Aburnin_it = np.zeros([nreplicates, tbvmax], np.float64)
Astderr_it = np.zeros([nreplicates, tbvmax], np.float64)
for i in range(nreplicates):
    for t0 in range(tbvmax):
        A_t = np.squeeze(A_it[i, t0:tmax])
        g = statisticalInefficiency(A_t)
        Aburnin_it[i,t0] = A_t.mean()
        Astderr_it[i,t0] = A_t.std() / np.sqrt((tmax-t0+1) / g)

Aburnin_mean_t = Aburnin_it.mean(0)
Aburnin_std_t  = Aburnin_it.std(0)

# Compute bias/variance tradeoff for fixed initial burn-in times.
Abias_mean_t = Aburnin_it.mean(0) - true_expectation
Abias_stderr_t = Aburnin_it.mean(0) / np.sqrt(nreplicates)
Astderr_mean_t = Aburnin_it.std(0)
Astderr_stderr_t = Aburnin_it.std(0) / np.sqrt(nreplicates)

#print ""
#print "BIAS-VARIANCE TRADEOFF FOR FIXED INITIAL BURN-IN"
#print "%8s   %10s %10s" % ("", "bias", "stderr")
#for t0 in range(t0max):
#    print "%8d : %10.6f %10.6f" % (t0, Abias_mean_t[t0], Astderr_mean_t[t0])
#print ""

# Compute estimates bias and variance using no equilibration, arbitrary equilibration, and optimal equilibration.
bias_i = dict()
stddev_i = dict()
schemes = ['noequil', 'optequil', 'fixedequil']
for scheme in schemes:
    bias_i[scheme] = np.zeros([nreplicates], np.float64)
    stddev_i[scheme] = np.zeros([nreplicates], np.float64)

for replicate in range(nreplicates):
    for scheme in schemes:
        if scheme == 'noequil':
            t0 = 0
        elif scheme == 'optequil':
            t0 = t0equil_i[replicate]
        elif scheme == 'fixedequil':
            t0 = int(tmax/2)
        else:
            raise Exception("scheme '%s' unknown" % scheme)

        # Extract timeseries for desired equilibration time t0.
        A_t = np.squeeze(A_it[replicate, t0:tmax])
        N = len(A_t)
        g = g_it[replicate, t0]
        # Compute statistics of estimate.
        bias_i[scheme][replicate] = A_t.mean() - true_expectation
        stddev_i[scheme][replicate] = A_t.std() / np.sqrt(N/g)

# Summarize error, bias, and variance statistics for different equilibration time selection schemes.
print ""
print "STATISTICS"
for scheme in schemes:
    print "%24s : error %10.6f bias %10.6f +- %10.6f stddev %10.6f +- %10.6f" % (scheme, np.sqrt((bias_i[scheme]**2).mean()), bias_i[scheme].mean(), bias_i[scheme].std()/np.sqrt(nreplicates), stddev_i[scheme].mean(), stddev_i[scheme].std()/np.sqrt(nreplicates))
print ""

#
# FIGURE 4: RMS ERROR FOR FIXED EQUILIBRATION TIME VS AUTOMATIC EQUILIBRATION TIME SELECTION
#

print "Creating RMS error figure..."

# Create plot as PDF.
filename = os.path.join(figure_directory, 'argon-rmse.pdf') # PDF file to write

x = np.arange(tbvmax) * ps_per_iteration # ps

pp = PdfPages(filename)

import pylab

fontsize=10

font = {'family' : 'sans-serif',
        'weight' : 'normal',
        'size'   : fontsize}

plt.rc('font', **font)

figure = pylab.figure(figsize=(7.5, 2.0), dpi=300)

nskip = 10 # number of samples to skip in uncertainty shading
hspace = 0.001 # spacing between subplots

# Plot RMSE for fixed global t0.
B = ((Aburnin_it - true_expectation)**2).mean(0)
dB = ((Aburnin_it - true_expectation)**2).std(0) / np.sqrt(nreplicates)

rmse_t0 = np.sqrt(B)
drmse_t0 = 0.5 * dB / rmse_t0
pylab.plot(x[0:tbvmax], rmse_t0, 'k-')
pylab.hold(True)
pylab.fill_between(x[0:tbvmax:nskip], rmse_t0[0:tbvmax:nskip]+2*drmse_t0[0:tbvmax:nskip], rmse_t0[0:tbvmax:nskip]-2*drmse_t0[0:tbvmax:nskip], facecolor='gray', edgecolor='gray', alpha=0.5, linewidth=0)

# Adjust axes.
oldaxis = pylab.axis()
oldaxis = (oldaxis[0], oldaxis[1], 0, 0.006)
pylab.axis([0, x[:t0max].max(), oldaxis[2], oldaxis[3]])


# Plot RMSE for automatically determined optimal t0.
rmse_optimal = np.sqrt((bias_i['optequil']**2).mean())
drmse_optimal = 0.5 * ((bias_i['optequil']**2).std() / np.sqrt(nreplicates)) / rmse_optimal
print "rmse_optimal %10.6f drmse_optimal %10.6f" % (rmse_optimal, drmse_optimal)
pylab.plot([x[0], x[tbvmax-1]], [rmse_optimal, rmse_optimal], 'r-')
pylab.fill_between([x[0], x[tbvmax-1]], (rmse_optimal+2*drmse_optimal)*np.array([1,1]), (rmse_optimal-2*drmse_optimal)*np.array([1,1]), facecolor='red', edgecolor='red', alpha=0.5, linewidth=0)

pylab.xlabel('$t_0$ / ps')
pylab.ylabel('$\delta \hat{\mathrm{A}}$')

figure.tight_layout()

# Write figure to PDF
pp.savefig()
pp.close()

#
# FIGURE 3: CREATE BIAS_VARIANCE FIGURE
#

print "Creating bias-variance tradeoff figure..."

# Create plot as PDF.
filename = os.path.join(figure_directory, 'argon-bias-variance.pdf') # PDF file to write

from matplotlib.backends.backend_pdf import PdfPages
pp = PdfPages(filename)

import pylab

fontsize=10

font = {'family' : 'sans-serif',
        'weight' : 'normal',
        'size'   : fontsize}

plt.rc('font', **font)

figure = pylab.figure(figsize=(3.5, 3.5), dpi=300)

nskip = 10 # number of samples to skip in uncertainty shading
hspace = 0.001 # spacing between subplots

from matplotlib.colors import Normalize
framelist = range(0, tbvmax)
norm = Normalize(framelist) # normalized value of frame number
from matplotlib.cm import ScalarMappable
ax = figure.add_subplot(1, 1, 1)
# Create ranbow colormap
cmap = plt.cm.get_cmap('rainbow')
sc = ax.scatter(Abias_mean_t, Astderr_mean_t, c=framelist, vmin=0, vmax=tbvmax, s=20, cmap=cmap, linewidths=0)
pylab.hold(True)
pylab.plot(bias_i['optequil'].mean(),  bias_i['optequil'].std(), 'kv')

# Add colorbar, make sure to specify tick locations to match desired ticklabels
pylab.colorbar(sc, orientation='vertical', shrink=0.70)

# Label plot
pylab.xlabel('bias')
pylab.ylabel('standard error')

#pylab.show()
figure.tight_layout()

pylab.axis([-0.0005, 0.006, -0.0005, 0.006])
pylab.axes().set_aspect('equal', adjustable='box')
pylab.axes().set_xticks([0.0, 0.002, 0.004, 0.006])
pylab.axes().set_yticks([0.0, 0.002, 0.004, 0.006])

# Write figure to PDF
pp.savefig()
pp.close()

#
# FIGURE 2: STATISTICAL INEFFICIENCY, NUMBER OF UNCORRELATED SAMPLES, AND BIAS AS A FUNCTION OF FIXED EQUILIBRATION TIME
#

print "Creating reverse cumulative averages figure..."

# Create plot as PDF.
filename = os.path.join(figure_directory, 'argon-reverse-cumulative-average.pdf') # PDF file to write

pp = PdfPages(filename)


fontsize=10

font = {'family' : 'sans-serif',
        'weight' : 'normal',
        'size'   : fontsize}

plt.rc('font', **font)

figure = pylab.figure(figsize=(7.5, 3.5), dpi=300)

nskip = 10 # number of samples to skip in uncertainty shading
hspace = 0.001 # spacing between subplots

#
# TOP PANEL: STATISTICAL INEFFICIENCY
#

subplot = pylab.subplot(311)
pylab.subplots_adjust(hspace=hspace)
pylab.hold(True)

pylab.fill_between(x[0:t0max:nskip], g_it[:,0:t0max:nskip].mean(0)+g_it[:,0:t0max:nskip].std(0), g_it[:,0:t0max:nskip].mean(0)-g_it[:,0:t0max:nskip].std(0), facecolor='gray', edgecolor='gray', alpha=0.5, linewidth=0)
pylab.plot(np.tile(x[0:t0max], [nreplicates,1]).T, g_it[:,:t0max].mean(0), 'k-')

subplot.set_xticks([]) # no x-tick labels

pylab.ylabel(r'$g$ / iterations', fontsize=fontsize)

# Adjust axes.
oldaxis = pylab.axis()
oldaxis = (oldaxis[0], oldaxis[1], 0, 125)
pylab.axis([0, x[:t0max].max(), oldaxis[2], oldaxis[3]])

# Plot t0equil.
pylab.plot(x[t0equil]*np.array([1,1]), [oldaxis[2], oldaxis[3]], 'r-', linewidth=3)

subplot.set_yticks([0, 25, 50, 75, 100, 125]) # no x-tick labels

#
# MIDDLE PANEL: NUMBER OF EFFECTIVELY UNCORRELATED SAMPLES
#

subplot = pylab.subplot(312)
pylab.subplots_adjust(hspace=hspace)
pylab.hold(True)

pylab.fill_between(x[0:t0max:nskip], N_it[:,0:t0max:nskip].mean(0)+N_it[:,0:t0max:nskip].std(0), N_it[:,0:t0max:nskip].mean(0)-N_it[:,0:t0max:nskip].std(0), facecolor='gray', edgecolor='gray', alpha=0.5, linewidth=0)
pylab.plot(np.tile(x[0:t0max], [nreplicates,1]).T, N_it[:,:t0max].mean(0), 'k-')

subplot.set_xticks([]) # no x-tick labels

pylab.ylabel(r'$N_\mathrm{eff}$', fontsize=fontsize)

# Adjust axes.
oldaxis = pylab.axis()
oldaxis = (oldaxis[0], oldaxis[1], 0, 50)
pylab.axis([0, x[:t0max].max(), oldaxis[2], oldaxis[3]])

#subplot.set_xticks([]) # no x-tick labels

# Plot t0equil.
pylab.plot(x[t0equil]*np.array([1,1]), [oldaxis[2], oldaxis[3]], 'r-', linewidth=3)
# Plot individual t0equil estimates.
#for replicate in range(nreplicates):
#    pylab.plot(x[t0equil_i[replicate]]*np.array([1,1]), [oldaxis[2], oldaxis[3]], 'k-', linewidth=0.5)

subplot.set_yticks([0, 10, 20, 30, 40, 50])

#
# BOTTOM PANEL: ERROR AS A FUNCTION OF BURN-IN PERIOD
#

subplot = pylab.subplot(313)
pylab.subplots_adjust(hspace=hspace)
pylab.hold(True)

pylab.fill_between(x[0:t0max:nskip], Aburnin_mean_t[0:t0max:nskip]+Aburnin_std_t[0:t0max:nskip], Aburnin_mean_t[0:t0max:nskip]-Aburnin_std_t[0:t0max:nskip], facecolor='gray', edgecolor='gray', alpha=0.5, linewidth=0)
pylab.plot([x[0], x[t0max]], [true_expectation, true_expectation], 'r--')
pylab.plot(x[0:t0max], Aburnin_mean_t[0:t0max], 'k-')

pylab.legend(['true expectation', 'discarding initial $[0,t_0]$'], fontsize=fontsize-2, frameon=False)

pylab.xlabel('initial simulation time $t_0$ / ps')
pylab.ylabel(r'$\left\langle\rho^*\right\rangle_{[t_0,T]}$', fontsize=fontsize)

# Adjust axes.
oldaxis = pylab.axis()
oldaxis = (oldaxis[0], oldaxis[1], 0.778, 0.794)
pylab.axis([0, x[:t0max].max(), oldaxis[2], oldaxis[3]])

# Plot t0equil.
pylab.plot(x[t0equil]*np.array([1,1]), [oldaxis[2], oldaxis[3]], 'r-', linewidth=3)

subplot.set_yticks([0.778, 0.782, 0.786, 0.790, 0.794])

#pylab.show()
figure.tight_layout()

# Write figure to PDF
pp.savefig()
pp.close()

