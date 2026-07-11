// Select the region
// Cerro Gordo County, Iowa
var counties = ee.FeatureCollection('TIGER/2018/Counties');

var selected = counties
  .filter(ee.Filter.eq('GEOID', '19033'));
var geometry = selected.geometry();
Map.centerObject(geometry, 12);
Map.addLayer(geometry, {color: 'red'}, 'Selected Region', false);
var embeddings = ee.ImageCollection('GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL');

var year = 2022;
var startDate = ee.Date.fromYMD(year, 1, 1);
var endDate = startDate.advance(1, 'year');

var filteredembeddings = embeddings
  .filter(ee.Filter.date(startDate, endDate))
  .filter(ee.Filter.bounds(geometry));

var embeddingsImage = filteredembeddings.mosaic();
// Use Cropland Data Layers (CDL) to obtain cultivated cropland
var cdl = ee.ImageCollection('USDA/NASS/CDL')
  .filter(ee.Filter.date(startDate, endDate))
  .first();
var cropLandcover = cdl.select('cropland');
var croplandMask = cdl.select('cultivated').eq(2).rename('cropmask');

// Visualize the crop mask
var croplandMaskVis = {min: 0, max: 1, palette: ['white', 'green']};
Map.addLayer(croplandMask.clip(geometry), croplandMaskVis, 'Crop Mask');// Mask all non-cropland pixels
var clusterImage = embeddingsImage.updateMask(croplandMask);
// Stratified random sampling
var training = clusterImage.addBands(croplandMask).stratifiedSample({
  numPoints: 1000,
  classBand: 'cropmask',
  region: geometry,
  scale: 10,
  tileScale: 16,
  seed: 100,
  dropNulls: true,
  geometries: true
});
// Stratified random sampling
var training = clusterImage.addBands(croplandMask).stratifiedSample({
  numPoints: 1000,
  classBand: 'cropmask',
  region: geometry,
  scale: 10,
  tileScale: 16,
  seed: 100,
  dropNulls: true,
  geometries: true
});
// Replace this with your asset folder
// The folder must exist before exporting
var exportFolder = 'projects/spatialthoughts/assets/satellite_embedding/';

var samplesExportFc = 'cluster_training_samples';
var samplesExportFcPath = exportFolder + samplesExportFc;

Export.table.toAsset({
  collection: training,
  description: 'Cluster_Training_Samples',
  assetId: samplesExportFcPath
});
// Use the exported asset
var training = ee.FeatureCollection(samplesExportFcPath);
print('Extracted sample', training.first());
Map.addLayer(training, {color: 'blue'}, 'Extracted Samples', false);
// Cluster the Satellite Embedding Image
var minClusters = 4;
var maxClusters = 5;

var clusterer = ee.Clusterer.wekaCascadeKMeans({
  minClusters: minClusters, maxClusters: maxClusters}).train({
  features: training,
  inputProperties: clusterImage.bandNames()
});

var clustered = clusterImage.cluster(clusterer);
Map.addLayer(clustered.randomVisualizer().clip(geometry), {}, 'Clusters');
// Calculate Cluster Areas
// 1 Acre = 4046.86 Sq. Meters
var areaImage = ee.Image.pixelArea().divide(4046.86).addBands(clustered);

var areas = areaImage.reduceRegion({
      reducer: ee.Reducer.sum().group({
      groupField: 1,
      groupName: 'cluster',
    }),
    geometry: geometry,
    scale: 10,
    maxPixels: 1e10
    });

var clusterAreas = ee.List(areas.get('groups'));

// Process results to extract the areas and create a FeatureCollection

var clusterAreas = clusterAreas.map(function(item) {
  var areaDict = ee.Dictionary(item);
  var clusterNumber = areaDict.getNumber('cluster').format();
  var area = areaDict.getNumber('sum');
  return ee.Feature(null, {cluster: clusterNumber, area: area});
});

var clusterAreaFc = ee.FeatureCollection(clusterAreas);
print('Cluster Areas', clusterAreaFc);
var selectedFc = clusterAreaFc.sort('area', false).limit(2);
print('Top 2 Clusters by Area', selectedFc);

var cornFeature = selectedFc.sort('area', false).first();
var soybeanFeature = selectedFc.sort('area').first();
var cornCluster = cornFeature.get('cluster');
var soybeanCluster = soybeanFeature.get('cluster');

print('Corn Area (Detected)', cornFeature.getNumber('area').round());
print('Corn Area (From Crop Statistics)', 163500);

print('Soybean Area (Detected)', soybeanFeature.getNumber('area').round());
print('Soybean Area (From Crop Statistics)', 110500);

// Select the clusters to create the crop map
var corn = clustered.eq(ee.Number.parse(cornCluster));
var soybean = clustered.eq(ee.Number.parse(soybeanCluster));

var merged = corn.add(soybean.multiply(2));
var cropVis = {min: 0, max: 2, palette: ['#bdbdbd', '#ffd400', '#267300']};
Map.addLayer(merged.clip(geometry), cropVis, 'Crop Map (Detected)');
// Add a Legend
var legend = ui.Panel({
  layout: ui.Panel.Layout.Flow('horizontal'),
  style: {position: 'bottom-center', padding: '8px 15px'}});

var addItem = function(color, name) {
  var colorBox = ui.Label({
    style: {color: '#ffffff',
      backgroundColor: color,
      padding: '10px',
      margin: '0 4px 4px 0',
    }
  });
  var description = ui.Label({
    value: name,
    style: {
      margin: '0px 10px 0px 2px',
    }
  });
  return ui.Panel({
    widgets: [colorBox, description],
    layout: ui.Panel.Layout.Flow('horizontal')
  });
};

var title = ui.Label({
  value: 'Legend',
  style: {
    fontWeight: 'bold',
    fontSize: '16px',
    margin: '0px 10px 0px 4px'
  }
});

legend.add(title);
legend.add(addItem('#ffd400', 'Corn'));
legend.add(addItem('#267300', 'Soybean'));
legend.add(addItem('#bdbdbd', 'Other Crops'));

Map.add(legend);

var cdl = ee.ImageCollection('USDA/NASS/CDL')
  .filter(ee.Filter.date(startDate, endDate))
  .first();
var cropLandcover = cdl.select('cropland');
var cropMap = cropLandcover.updateMask(croplandMask).rename('crops');

// Original data has unique values for each crop ranging from 0 to 254
var cropClasses = ee.List.sequence(0, 254);
// We remap all values as following
// Crop     | Source Value | Target Value
// Corn     | 1            | 1
// Soybean  | 5            | 2
// All other| 0-255        | 0
var targetClasses = ee.List.repeat(0, 255).set(1, 1).set(5, 2);
var cropMapReclass = cropMap.remap(cropClasses, targetClasses).rename('crops');

var cropVis = {min: 0, max: 2, palette: ['#bdbdbd', '#ffd400', '#267300']};
Map.addLayer(cropMapReclass.clip(geometry), cropVis, 'Crop Landcover (CDL)');