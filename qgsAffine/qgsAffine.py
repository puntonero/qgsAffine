from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ui import Ui_ui

from qgis.core import *
from qgis.gui import *

#from ui_control import ui_Control
import resources
from multiprocessing import Pool
import time

def work(fid):
	affineClass = qgsAffine(IFACE)
	result = getattr(affineClass, 'moving')(fid, a,b,c,d,tx,ty)
	
class qgsAffine(QDialog, Ui_ui):

	def __init__(self, iface):
		self.iface = iface
		global IFACE
		IFACE = iface
		QDialog.__init__(self, iface.mainWindow())
		self.setupUi(self)
		
	def initGui(self):
		# create action that will start plugin configuration
		self.action = QAction(QIcon(":plugins/qgsAffine/icon.svg"), "Affine (Rotation, Translation, Scale)", self.iface.mainWindow())
		self.action.setWhatsThis("Configuration for test plugin")
		QObject.connect(self.action, SIGNAL("triggered()"), self.run)
	
		# add toolbar button and menu item
		self.iface.addToolBarIcon(self.action)

		#add to Vector menu
		nextAction = self.iface.mainWindow().menuBar().actions()[3].menu().actions()[3]
		self.iface.mainWindow().menuBar().actions()[3].menu().insertAction(nextAction,self.action)
		if hasattr(self.iface, "addPluginToVectorMenu"):
			self.iface.addPluginToVectorMenu("&Geoprocessing Tools", self.action)
		else:
			self.iface.addPluginToMenu("&Geoprocessing Tools", self.action)
		#self.action.setEnabled(False)
		
		
		#INSERT EVERY SIGNAL CONECTION HERE!
		QObject.connect(self.pushButtonRun,SIGNAL("clicked()"),self.affine)
		QObject.connect(self.pushButtonInvert,SIGNAL("clicked()"),self.invert)
		QObject.connect(self.pushButtonClose,SIGNAL("clicked()"),self.finish)


	def unload(self):
		# remove the plugin menu item and icon
		if hasattr(self.iface, "addPluginToVectorMenu"):
			self.iface.removePluginVectorMenu("&Geoprocessing Tools", self.action)
		else:
			self.iface.removePluginMenu("&Geoprocessing Tools", self.action)
		self.iface.removeToolBarIcon(self.action)
	
	
	def run(self):
		# create and show a configuration dialog or something similar
		flags = Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowMaximizeButtonHint  # QgisGui.ModalDialogFlags
		self.comboBoxLayer.clear()
		for item in self.listlayers(0):
			self.comboBoxLayer.addItem(item)
		self.timeLabel.setText("")
		self.show()
	
	def listlayers(self,layertype):
		layersmap=QgsMapLayerRegistry.instance().mapLayers()
		layerslist=[]
		for (name,layer) in layersmap.iteritems():
			if (layertype==layer.type()):
				layerslist.append(layer.name())
		return layerslist
	
	def getLayerByName(self,layername):
		layersmap=QgsMapLayerRegistry.instance().mapLayers()
		for (name,layer) in layersmap.iteritems():
			if (layername==layer.name()):
				return layer
	def setaffine(self):
		global a
		global b
		global c
		global d
		global tx
		global ty
		a = self.a=self.spinA.value()
		b = self.b=self.spinB.value()
		tx = self.tx=self.spinTx.value()
		c = self.c=self.spinC.value()
		d = self.d=self.spinD.value()
		ty = self.ty=self.spinTy.value()
		

	#Now these are the SLOTS
	def affine(self):
		self.setaffine()
		self.doaffine()
		
	def invert(self):
		# matrix form: x' = A x + b
		# --> x = A^-1 x' - A^-1 b
		# A^-1 = [d -b; -c a] / det A
		# only valid if det A = a d - b c != 0
		self.setaffine()
		det = self.a*self.d - self.b*self.c
		if det == 0:
			warn=QgsMessageViewer()
			warn.setMessageAsPlainText("Transformation is not invertable.")
			warn.showMessage()
			return
		a=self.d/det
		b=-self.b/det
		c=-self.c/det
		d=self.a/det
		tx=-a*self.tx-b*self.ty
		ty=-c*self.tx-d*self.ty
		self.spinA.setValue(a)
		self.spinB.setValue(b)
		self.spinC.setValue(c)
		self.spinD.setValue(d)
		self.spinTx.setValue(tx)
		self.spinTy.setValue(ty)
		self.setaffine()

	def finish(self):
		self.close()
		
	def moving(self, fid, a,b,c,d,tx,ty):
		vlayer=LAYER
		features[fid]=QgsFeature()
		if not vlayer.getFeatures( QgsFeatureRequest().setFilterFid( fid ) ).nextFeature( features[fid] ):
			return 0
		result[fid]=features[fid].geometry()
		i=start
		provider=vlayer.dataProvider()
		vertex=result[fid].vertexAt(i)
		print a, b, c, d, tx, ty
		while (vertex!=QgsPoint(0,0)):
					# matrix form: x' = A x + b
					# x' = a x + b y + tx
					# y' = c x + d y + ty
			newx=a*vertex.x()+b*vertex.y()+tx
			newy=c*vertex.x()+d*vertex.y()+ty
			#geom.
			#print vertex.x(), vertex.y(), newx, newy
			#geom = QgsGeometry.fromPoint(QgsPoint(newx,newy))
			print vertex.x(), vertex.y()
			print newx,newy,fid,i
			vlayer.moveVertex(newx,newy,fid,i)
			i+=1
			vertex=result[fid].vertexAt(i)
	
	def doaffine(self):
		warn=QgsMessageViewer()
		vlayer=self.getLayerByName(self.comboBoxLayer.currentText())
		global LAYER
		LAYER = vlayer
		if (self.radioButtonWholeLayer.isChecked()):
			vlayer.removeSelection()
			vlayer.invertSelection()
		if vlayer is None:
			warn.setMessageAsPlainText("Select a layer to transform.")
			warn.showMessage()
			return
		featids=vlayer.selectedFeaturesIds()
		provider=vlayer.dataProvider()
		global result
		global features
		global start
		result={}
		features={}
		if (vlayer.geometryType()==2):
			start=1
		else:
			start=0
		print vlayer.name()
		if (not vlayer.isEditable()):
			warn.setMessageAsPlainText("Layer not in edit mode.")
			warn.showMessage()
		else:
			start_time = time.time()
			pool = Pool()
			pool.map(work, featids)
			pool.close()
			pool.join()
			#for fid in featids:
				#features[fid]=QgsFeature()
				#if not vlayer.getFeatures( QgsFeatureRequest().setFilterFid( fid ) ).nextFeature( features[fid] ):
				#	continue;
				#result[fid]=features[fid].geometry()
				#i=start
				#vertex=result[fid].vertexAt(i)
				#while (vertex!=QgsPoint(0,0)):
				#			# matrix form: x' = A x + b
				#			# x' = a x + b y + tx
				#			# y' = c x + d y + ty
				#	newx=a*vertex.x()+b*vertex.y()+tx
				#	newy=c*vertex.x()+d*vertex.y()+ty
				#	#geom.
				#	#print vertex.x(), vertex.y(), newx, newy
				#	vlayer.moveVertex(newx,newy,fid,i)
				#	#print vertex.x,vertex.y,newx,newy,fid,i
				#	i+=1
				#	vertex=result[fid].vertexAt(i)
		self.timeLabel.setText("Enlapsed time: %s" % time.strftime("%Hh %Mm %Ss", time.gmtime(time.time() - start_time)))
	    #vlayer.commitChanges()
	    #vlayer.updateExtents()
	    #vlayer.updateGeometryValues(result)
	    
		#self.iface.mapCanvas().zoomToSelected()
		self.iface.mapCanvas().refresh()
		#print "ok"

