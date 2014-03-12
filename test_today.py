import MDSplus as MDS
import matplotlib.pyplot as pt
shot = 73511
Tr = MDS.Tree('h1data',shot)
fig, ax = pt.subplots(nrows=3, ncols=2,sharex=1)
for j,i in enumerate(['7','8','9']):
    node = Tr.getNode('mirnov.ACQ132_%s:input_32'%(i))
    ax[j,0].plot(node.dim_of().data(), node.data())

for i in [1,2,3]:
    node = Tr.getNode('mirnov.ACQ132_8:input_0%d'%(i))
    ax[i-1,1].plot(node.dim_of().data(), node.data())
    
ax[0,0].set_xlim([-0.03,0.05])
fig.canvas.draw()
fig.show()
