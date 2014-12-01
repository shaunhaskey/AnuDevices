""" Code related to reading RF tuning information from MDSplus
Reads straight from raw signals
See also tuning_box_H1.py for the tuning circuit itself.
"""
# Following are examples for testing the tuning algorithm
# shot 73880 is Ar tune in argon, 81 is hydrogen tune
# Also the selected 6500 amp shots when tuning in Hy should be useful

"""
C_1 = MDS.Tree('h1data',73880).getNode('.log.heating:COOLED_ANT:RFTUNE1').data()
C_2 = MDS.Tree('h1data',73880).getNode('.log.heating:COOLED_ANT:RFTUNE2').data()


C_1 = MDS.Tree('h1data',73880).getNode('.log.heating:COOLED_ANT:RFTUNE1').data()

#P_REV_I = (A14_6:INPUT_3 - .311F0) 
#P_REV_Q = (A14_6:INPUT_4 - .109F0)

import pylab as pl

tim = MDS.Tree('h1data',73881).getNode('.RF:A14_6:INPUT_3').dim_of().data()
P_REV_I = (MDS.Tree('h1data',73881).getNode('.RF:A14_6:INPUT_3').data()) - .311
P_REV_Q = (MDS.Tree('h1data',73881).getNode('.RF:A14_6:INPUT_4').data()) - .109
pl.plot(tim, P_REV_I)
pl.plot(tim, P_REV_Q)
"""

import pylab as pl
import numpy as np
import MDSplus as MDS

#pl.rcParams['legend.fontsize']='small'

def cpx(r,i):
    """ a version of the complex() function that works for arrays.
    """
    return(r + 1j* i)

def plotc(t,z,label='_', hold=0, color=None, polar=False, ax=None, **kwargs):
    """ plot a complex quantity - dashed for image, only one entry in 
    legend labels
    """
    if ax == None: ax = pl.gca()
    if color != None: kwargs.update(color = color)
    if polar:
        plt = ax.plot(np.real(z),  np.imag(z), label=label, hold=hold, **kwargs)
        ax=pl.gca()
        rad=max(abs(z))
        circ= ax.Circle((0,0), radius=rad, ls='dotted', fill=False, 
                        color=plt[0].get_color())
        ax.add_patch(circ)
        ax.set_aspect('equal')
        
    else:
        realplot = ax.plot(t, np.real(z), label=label, 
                            **kwargs)
        ax.plot(t, np.imag(z), ':', 
                color=realplot[0].get_color(), label='_', **kwargs)


from warnings import warn

ForRevExcept = None #MDS.TdiException

""" organise data at two levels 
    1/ by channel pair    (4,1,2) is the key for a14_4, chans 1,2
    2/ by physical name   I_top is the current in physical units, including
                  direcional coupler cal (with f)
"""
def ofs(v12):
    return(np.array(v12).astype(np.double))
def gainf(g,row1,row2):
    return((0.9, np.array([row1, row2]).astype(np.double)))
cdata = {
    (4,1,2): 
    dict(offset = ofs([-0.02,0.103]), gain = gainf(1, [1,0],[0,1])),
    (4,3,4): 
    dict(offset = ofs([0.219,0.115]), gain = gainf(1, [1,0],[0,1])),
    (4,5,6): 
    dict(offset = ofs([0.104,0.121]), gain = gainf(1, [1,0],[0,1])),
    (6,1,2): 
    dict(offset = ofs([0.136,0.047]), gain = gainf(1, [1,0],[0,1])),
    (6,3,4): 
    dict(offset = ofs([0.301,0.105]), gain = gainf(1, [1,0],[0,1])),
    (6,5,6): 
    dict(offset = ofs([-0.069,0.074]), gain = gainf(1, [1,0],[0,1])),
        }

pdata = dict(
    top_iant = (4,1,2),
    bot_iant = (4,3,4),
    top_fwd = (4,5,6),
    bot_fwd = (6,1,2),
    top_rev = (6,3,4),
    bot_rev = (6,5,6)
    )

class RF_data():
    def __init__(self, treename = 'h1data', shot=0):
        self.shot = shot
        self.treename = treename
        self.tree = MDS.Tree(treename, shot)

    def get_chan(self, chan=(4,1,2)):
        """
        if tr is None:
        print('please supply an open tree = debugging with default tree, current shot')
            tr = MDS.Tree('h1data', 0 )
        """
        ".RF:A14_4:INPUT_1"
        (n,c1,c2) = chan
        tr = self.tree
        node1 = ".RF.A14_{n}:INPUT_{c}".format(n=n, c=c1)
        node2 = ".RF.A14_{n}:INPUT_{c}".format(n=n, c=c2)
        v1 = tr.getNode(node1).data() - cdata[chan]['offset'][0]
        v2 = tr.getNode(node2).data() - cdata[chan]['offset'][1]
        t = tr.getNode(node1).dim_of().data()
        pair = cdata[chan]['gain'][0] * np.dot(cdata[chan]['gain'][1],[v1,v2])
        return(t,cpx(*pair))  # the * because cpx expects 2 args - cvt arr to 2 arrs

    def get_sig(self, sig):
        if sig not in pdata.keys(): 
            raise LookupError('{s} not in known signals {keys}'
                              .format(s=sig, keys=pdata.keys()))
        chan = pdata[sig]
        t,s = self.get_chan(chan)
        return(t,s)


def show_RF(shot=0, hold=0, tree='h1data', quiet=1, ant='top', offs=None, facts = None, plots=2, polar=True, minfwd=None):
    """ 
    THe original clunker version:
    quiet = 1 means suppress exceptions, just returning status
    plots = 0 (none), 1(just rho), 2(rho and forward and rev)
    offs = None - take intelligent defaults. (also facts = factors before offs)
    Typical fix for 75084, bot: facts=[1,1.72,1,0.88], offs=[0.165,0.135,.257,0.077])
    """ 

    if offs == None: offs = np.zeros(8)
    if facts == None: facts = np.ones(8)

    if facts == None:
        if ant=='bot':
            facts[0:4]=[1,1.72,1,0.88]
        elif ant=='topfbotr':
            facts[0:4]=[1,1.72,1,0.88]

    if offs == None:
        if ant=='bot':
            offs[0:4]=[0.14,0.09,.257,0.077]
        if ant=='topfbotr':
            offs[0:4]=[0.14,0.09,.257,0.077]




    try: 
        tr = MDS.Tree(tree, shot)
    except:
        tr = MDS.Tree(tree, shot)

    if shot == 0: shot = tr.getCurrent(tree)

    status = 1
    try:
        C_1 = tr.getNode('.log.heating:COOLED_ANT:RFTUNE1').data()
        C_2 = tr.getNode('.log.heating:COOLED_ANT:RFTUNE2').data()
    except MDS.TdiException:
        msg = 'RFTune values shot {0}'.format(shot)
        if quiet == 0: 
            raise LookupError, msg
        else:
            warn(msg)
            C_1 = np.nan
            C_2 = np.nan
#P_REV_I = (A14_6:INPUT_3 - .311F0) 
#P_REV_Q = (A14_6:INPUT_4 - .109F0)


    try:
        top_node = ['.RF:A14_4:INPUT_1', '.RF:A14_4:INPUT_2']
        bot_node = ['.RF:A14_4:INPUT_3', '.RF:A14_4:INPUT_4']

        top_fwd_node = ['.RF:A14_4:INPUT_5', '.RF:A14_4:INPUT_6']
        bot_fwd_node = ['.RF:A14_6:INPUT_1','.RF:A14_6:INPUT_2']

        if ant == 'top':
            fwd_node = ['.RF:A14_4:INPUT_5', '.RF:A14_4:INPUT_6']
            rev_node = ['.RF:A14_6:INPUT_3', '.RF:A14_6:INPUT_4']

        elif ant == 'topfbotr':
            fwd_node = ['.RF:A14_6:INPUT_1','.RF:A14_6:INPUT_2']
            rev_node = ['.RF:A14_6:INPUT_5','.RF:A14_6:INPUT_6']

        elif ant == 'bot':
            fwd_node = ['.RF:A14_6:INPUT_1','.RF:A14_6:INPUT_2']
            rev_node = ['.RF:A14_6:INPUT_5','.RF:A14_6:INPUT_6']

        else:
            raise ValueError('antenna {0} not known - "top","bot","topfbotr"'
                             .format(ant))

        tim = tr.getNode(fwd_node[0]).dim_of().data()
        I_TOP_I = facts[4]*(tr.getNode(top_node[0]).data()) - offs[4]
        I_TOP_Q = facts[5]*(tr.getNode(top_node[1]).data()) - offs[5]

        I_BOT_I = facts[6]*(tr.getNode(bot_node[0]).data()) - offs[6]
        I_BOT_Q = facts[7]*(tr.getNode(bot_node[1]).data()) - offs[7]

        P_FWD_I = facts[0]*(tr.getNode(fwd_node[0]).data()) - offs[0]
        P_FWD_Q = facts[1]*(tr.getNode(fwd_node[1]).data()) - offs[1]

        P_REV_I = facts[2]*(tr.getNode(rev_node[0]).data()) - offs[2]
        P_REV_Q = facts[3]*(tr.getNode(rev_node[1]).data()) - offs[3]
    except ForRevExcept, errmsg:
        msg ='Forward/Reflected data shot {0}'.format(shot)
        raise LookupError, '||'.join([errmsg[0],fwd_node,msg])

    titl = "Shot {0}, C_1 = {1}, C_2 = {2}".format(shot, C_1, C_2)

    antname = ant

    titl = antname + ', ' +titl

    if (1):
        TOP_FOR_I = facts[4]*(tr.getNode(top_fwd_node[0]).data()) - offs[4]
        TOP_FOR_Q = facts[5]*(tr.getNode(top_fwd_node[1]).data()) - offs[5]

        BOT_FOR_I = facts[4]*(tr.getNode(bot_fwd_node[0]).data()) - offs[4]
        BOT_FOR_Q = facts[5]*(tr.getNode(bot_fwd_node[1]).data()) - offs[5]

        I_BOT_I = facts[6]*(tr.getNode(bot_node[0]).data()) - offs[6]
        I_BOT_Q = facts[7]*(tr.getNode(bot_node[1]).data()) - offs[7]

    fv = cpx(P_FWD_I,P_FWD_Q)
    rv = cpx(P_REV_I,P_REV_Q)
    i_top = cpx(I_TOP_I, I_TOP_Q)
    i_bot = cpx(I_BOT_I, I_BOT_Q)
    top_fwd = cpx(TOP_FOR_I, TOP_FOR_Q)
    bot_fwd = cpx(BOT_FOR_I, BOT_FOR_Q)

    pl.figure()
    pl.subplot(221)
    if plots > 1: # details
        if polar:
            plotc(tim, top_fwd,marker='.',alpha=0.2,ms=4, polar=polar, label='top_fwd')
            #pl.xlabel(fwd_node[0])
            #pl.ylabel(fwd_node[1])
            plotc(tim, bot_fwd,marker='.',alpha=0.2,ms=4, polar=polar, label='bot_fwd',hold=1)
            pl.legend(prop={'size':'x-small'})
            pl.title('Shot {s}'.format(s=shot))
            pl.subplot(222)
            
            plotc(tim, i_top,marker='.',alpha=0.2,ms=4, polar=polar, label='i_top')
            #pl.xlabel(fwd_node[0])
            #pl.ylabel(fwd_node[1])
            plotc(tim, i_bot,marker='.',alpha=0.2,ms=4, polar=polar, label='i_bot',hold=1)
            pl.legend()
            pl.title('Shot {s}'.format(s=shot))
            pl.subplot(223)
            

            plotc(tim, fv, polar=polar, label=antname + 'fwd')
            pl.xlabel(fwd_node[0])
            pl.ylabel(fwd_node[1])
            plotc(tim, rv, polar=polar, label=antname + 'rev',hold=1)
        else:
            pl.plot(tim, P_FWD_I, hold=hold, label='Fwd Re')
            pl.plot(tim, P_FWD_Q, label = 'Im {0}'.format(shot))
            pl.plot(tim, P_REV_I, hold=1, label='Rev Re')
            pl.plot(tim, P_REV_Q, label = 'Im {0}'.format(shot))
            pl.xlim(-1,1)
            pl.ylim(-1,1)

        pl.legend()
        pl.title(titl) 


    if plots==1: #just rho
        pl.figure()
        rho = rv/fv 
        if minfwd == None: minfwd = 0.05 * np.max(np.abs(fv))
        w = np.where(np.abs(fv) < minfwd)[0]
        rho[w] = np.nan
        plotc(tim, rho, label = 'rho '+ant+', shot = {0}'.format(shot),polar=polar)
        pl.title('S11 '+titl) 
        pl.show()

    return({'rev': cpx(P_REV_I, P_REV_Q), 'fwd': cpx(P_FWD_I, P_FWD_Q),
            'time': tim, 'tune': [C_1, C_2]}, status)

if __name__ == "__main__":
    # plotc(*get_sig('top_iant'), label='top_iant')
    print 'hello'
    import sys
    if len(sys.argv) > 1: shot = int(sys.argv[1])
    else: shot = 0
    tr = RF_data(shot=shot)
    fig, axs = pl.subplots(4,2,sharex='all')
    for i,sig in enumerate(pdata.keys()):
        ax = axs.flatten()[i]
        plotc(*tr.get_sig(sig), label=sig+str(pdata[sig]),ax=ax)
        ax.legend(prop={'size':'x-small'})        

    axph = axs.flatten()[-1]
    axph.plot(tr.get_sig('top_iant')[0],
                  np.angle(tr.get_sig('top_iant')[1]/tr.get_sig('bot_iant')[1],
                           np.degrees),label='rel. ant phase (deg)')
    axph.plot(tr.get_sig('top_fwd')[0],
                  np.angle(tr.get_sig('top_fwd')[1]/tr.get_sig('bot_fwd')[1],
                           np.degrees),label='rel. fwd phase')
    axph.legend(prop={'size':'x-small'})        

    pl.suptitle(shot)
    pl.show()
    """
    for (i,s) in enumerate(range(73989,73996)):
        pl.subplot(3,3,i+1)
        polar=True
        show_RF(s, plots=2, polar=polar)
        pl.ylim(-1,1)
        if polar == False: pl.xlim(0,0.1)
    """
