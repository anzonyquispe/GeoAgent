'use strict';

/**
 * Headless runner for Assignment 2.
 *
 * Usage:
 *   node gee_node_runner.js auth
 *   node gee_node_runner.js check
 *   node gee_node_runner.js prepare
 *   node gee_node_runner.js analyze
 *
 * Required environment variables:
 *   GEE_PROJECT
 *   GEE_KEY_PATH
 *   GEE_GLORICE_ASSET
 *   GEE_FIRE_ASSET
 *   GEE_OUTPUT_DIR
 *
 * Optional:
 *   GEE_MIN_CLUSTERS (default 5)
 *   GEE_MAX_CLUSTERS (default 7)
 */

const fs = require('fs');
const path = require('path');
const ee = require('@google/earthengine');

const MODE = process.argv[2] || 'check';
const PROJECT = process.env.GEE_PROJECT;
const KEY_PATH = process.env.GEE_KEY_PATH;
const GLORICE_ASSET = process.env.GEE_GLORICE_ASSET;
const FIRE_ASSET = process.env.GEE_FIRE_ASSET;
const OUTPUT_DIR = process.env.GEE_OUTPUT_DIR || path.join(__dirname, 'outputs');
const MIN_CLUSTERS = Number(process.env.GEE_MIN_CLUSTERS || 5);
const MAX_CLUSTERS = Number(process.env.GEE_MAX_CLUSTERS || 7);

function requireSetting(name, value) {
  if (!value) {
    throw new Error(`Falta la variable de entorno ${name}.`);
  }
}

function validateConfiguration() {
  requireSetting('GEE_PROJECT', PROJECT);
  requireSetting('GEE_KEY_PATH', KEY_PATH);
  if (MODE === 'check' || MODE === 'analyze') {
    requireSetting('GEE_GLORICE_ASSET', GLORICE_ASSET);
    requireSetting('GEE_FIRE_ASSET', FIRE_ASSET);
  }
  if (!fs.existsSync(KEY_PATH)) {
    throw new Error(`No se encontró la llave JSON: ${KEY_PATH}`);
  }
  if (!Number.isInteger(MIN_CLUSTERS) || !Number.isInteger(MAX_CLUSTERS)) {
    throw new Error('GEE_MIN_CLUSTERS y GEE_MAX_CLUSTERS deben ser enteros.');
  }
  if (MIN_CLUSTERS < 2 || MAX_CLUSTERS < MIN_CLUSTERS) {
    throw new Error('El rango de clusters no es válido.');
  }
}

async function checkAuthentication() {
  const base = buildBaseAnalysis();
  const checks = ee.Dictionary({
    project: PROJECT,
    bellavista_features: base.selected.size(),
    alphaearth_bands: base.embeddingsImage.bandNames().size()
  });
  const result = await evaluate(checks);
  writeJson('gee_auth_check.json', result);
  console.log('Autenticación e inicialización de Earth Engine verificadas.');
}

function authenticateAndInitialize() {
  const privateKey = JSON.parse(fs.readFileSync(KEY_PATH, 'utf8'));
  return new Promise((resolve, reject) => {
    ee.data.authenticateViaPrivateKey(
      privateKey,
      () => {
        ee.initialize(
          null,
          null,
          resolve,
          (error) => reject(new Error(`Error al inicializar Earth Engine: ${error}`)),
          null,
          PROJECT
        );
      },
      (error) => reject(new Error(`Error de autenticación: ${error}`))
    );
  });
}

function evaluateOnce(serverObject) {
  return new Promise((resolve, reject) => {
    serverObject.evaluate((result, error) => {
      if (error) {
        reject(new Error(typeof error === 'string' ? error : JSON.stringify(error)));
      } else {
        resolve(result);
      }
    });
  });
}

async function evaluate(serverObject, maxAttempts = 4) {
  let lastError;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      return await evaluateOnce(serverObject);
    } catch (error) {
      lastError = error;
      if (attempt === maxAttempts) {
        break;
      }
      const delayMs = 2000 * Math.pow(2, attempt - 1);
      console.warn(
        `evaluate() falló (intento ${attempt}/${maxAttempts}); reintentando en ${delayMs / 1000}s: ${error.message}`
      );
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }
  throw lastError;
}

function writeJson(fileName, value) {
  fs.mkdirSync(OUTPUT_DIR, {recursive: true});
  const outputPath = path.join(OUTPUT_DIR, fileName);
  fs.writeFileSync(outputPath, JSON.stringify(value, null, 2), 'utf8');
  console.log(`Resultado guardado: ${outputPath}`);
  return outputPath;
}

function buildBaseAnalysis() {
  const gaul2 = ee.FeatureCollection('FAO/GAUL/2015/level2');
  const selected = gaul2
    .filter(ee.Filter.eq('ADM1_NAME', 'San Martín'))
    .filter(ee.Filter.eq('ADM2_NAME', 'Bellavista'));
  const geometry = selected.geometry();

  const year = 2019;
  const startDate = ee.Date.fromYMD(year, 1, 1);
  const endDate = startDate.advance(1, 'year');
  const embeddingsImage = ee.ImageCollection('GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL')
    .filter(ee.Filter.date(startDate, endDate))
    .filter(ee.Filter.bounds(geometry))
    .mosaic();

  const worldCover = ee.Image('ESA/WorldCover/v200/2021').select('Map');
  const cropMask = worldCover.eq(40).rename('cropmask').clip(geometry);
  const clusterImage = embeddingsImage.updateMask(cropMask);
  const training = clusterImage.addBands(cropMask).stratifiedSample({
    numPoints: 800,
    classBand: 'cropmask',
    region: geometry,
    scale: 30,
    tileScale: 16,
    seed: 100,
    dropNulls: true,
    geometries: false
  });

  return {
    selected,
    geometry,
    embeddingsImage,
    cropMask,
    clusterImage,
    training
  };
}

async function checkAccess() {
  const base = buildBaseAnalysis();
  const gloRice = ee.Image(GLORICE_ASSET);
  const fires = ee.FeatureCollection(FIRE_ASSET).filterBounds(base.geometry);
  const checks = ee.Dictionary({
    bellavista_features: base.selected.size(),
    alphaearth_bands: base.embeddingsImage.bandNames().size(),
    glorice_bands: gloRice.bandNames(),
    fire_points_bellavista: fires.size()
  });
  const result = await evaluate(checks);
  writeJson('gee_preflight.json', result);
  console.log('Autenticación, catálogo y Assets verificados correctamente.');
}

async function prepareTraining() {
  const base = buildBaseAnalysis();
  const training = await evaluate(base.training);
  if (!training || !training.features || training.features.length === 0) {
    throw new Error('GEE no devolvió muestras de entrenamiento.');
  }
  writeJson('training_bellavista_2019.json', training);
  console.log(`Muestras descargadas: ${training.features.length}`);
}

function buildRiceAnalysis(base) {
  const clusterer = ee.Clusterer.wekaCascadeKMeans({
    minClusters: MIN_CLUSTERS,
    maxClusters: MAX_CLUSTERS
  }).train({
    features: base.training,
    inputProperties: base.clusterImage.bandNames()
  });
  const clustered = base.clusterImage.cluster(clusterer).rename('cluster');

  const gloRiceArea = ee.Image(GLORICE_ASSET)
    .rename('rice_area_ha')
    .clip(base.geometry);
  const gloRiceProjection = gloRiceArea.projection();
  const gloRiceCellAreaHa = ee.Image.pixelArea()
    .divide(10000)
    .reproject(gloRiceProjection);
  const riceFraction = gloRiceArea
    .divide(gloRiceCellAreaHa)
    .clamp(0, 1)
    .rename('rice_fraction');

  const pixelAreaHa = ee.Image.pixelArea().divide(10000).rename('area_ha');
  const totalAreaByCluster = pixelAreaHa.addBands(clustered).reduceRegion({
    reducer: ee.Reducer.sum().group({groupField: 1, groupName: 'cluster'}),
    geometry: base.geometry,
    scale: 30,
    maxPixels: 1e11,
    tileScale: 16
  });
  const riceAreaImage = pixelAreaHa
    .multiply(riceFraction)
    .rename('rice_area_est');
  const riceAreaByCluster = riceAreaImage.addBands(clustered).reduceRegion({
    reducer: ee.Reducer.sum().group({groupField: 1, groupName: 'cluster'}),
    geometry: base.geometry,
    scale: 30,
    maxPixels: 1e11,
    tileScale: 16
  });

  const totalFc = ee.FeatureCollection(
    ee.List(totalAreaByCluster.get('groups')).map((item) => {
      const dictionary = ee.Dictionary(item);
      return ee.Feature(null, {
        cluster: dictionary.getNumber('cluster').format(),
        area_total_ha: dictionary.getNumber('sum')
      });
    })
  );
  const riceFc = ee.FeatureCollection(
    ee.List(riceAreaByCluster.get('groups')).map((item) => {
      const dictionary = ee.Dictionary(item);
      return ee.Feature(null, {
        cluster: dictionary.getNumber('cluster').format(),
        area_arroz_ha: dictionary.getNumber('sum')
      });
    })
  );
  const joinFilter = ee.Filter.equals({leftField: 'cluster', rightField: 'cluster'});
  const joined = ee.Join.inner().apply(totalFc, riceFc, joinFilter);
  const clusterStats = ee.FeatureCollection(joined.map((pair) => {
    const left = ee.Feature(pair.get('primary'));
    const right = ee.Feature(pair.get('secondary'));
    const totalArea = left.getNumber('area_total_ha');
    const riceArea = right.getNumber('area_arroz_ha');
    const riceShare = riceArea.divide(totalArea);
    return ee.Feature(null, {
      cluster: left.get('cluster'),
      area_total_ha: totalArea,
      area_arroz_ha: riceArea,
      proporcion_arroz: riceShare,
      mayoria_arroz_50pct: riceShare.gt(0.5)
    });
  }));

  // Se conserva la decisión metodológica documentada: si ningún cluster supera
  // 50 %, se usa el cluster con la mayor proporción relativa de GloRice-I.
  const majorityCount = clusterStats
    .filter(ee.Filter.eq('mayoria_arroz_50pct', 1))
    .size();
  const maxRiceShare = clusterStats.aggregate_max('proporcion_arroz');
  const clusterStatsRanked = clusterStats.map((feature) => {
    const isMajority = ee.Number(feature.get('mayoria_arroz_50pct'));
    const isRelativeMaximum = ee.Number(feature.get('proporcion_arroz')).eq(maxRiceShare);
    const riceLabel = ee.Number(
      ee.Algorithms.If(majorityCount.gt(0), isMajority, isRelativeMaximum)
    );
    return feature.set({
      etiqueta_arroz: riceLabel,
      criterio_aplicado: ee.Algorithms.If(
        majorityCount.gt(0),
        'mayoria_mayor_50pct',
        'maxima_proporcion_relativa'
      )
    });
  });
  const riceClusterIds = clusterStatsRanked
    .filter(ee.Filter.eq('etiqueta_arroz', 1))
    .aggregate_array('cluster')
    .map((clusterId) => ee.Number.parse(clusterId));
  const riceMask = clustered.remap(
    riceClusterIds,
    ee.List.repeat(1, riceClusterIds.length()),
    0
  ).rename('is_rice_cluster').clip(base.geometry);

  return {
    clustered,
    riceFraction,
    clusterStatsRanked,
    riceMask,
    majorityCount
  };
}

function buildFireAnalysis(base, rice) {
  const years = [2017, 2018, 2019];
  const viirsBellavista = ee.FeatureCollection(FIRE_ASSET)
    .filterBounds(base.geometry)
    .map((feature) => {
      const date = ee.Date.parse('YYYY-MM-dd', ee.String(feature.get('acq_date')));
      return feature.set({
        fecha_millis: date.millis(),
        anio: date.get('year')
      });
    });
  const viirsWithClass = rice.riceMask.sampleRegions({
    collection: viirsBellavista,
    properties: ['acq_date', 'fecha_millis', 'anio'],
    scale: 30,
    geometries: false,
    tileScale: 16
  });

  const riceAreaKm2 = ee.Image.pixelArea()
    .divide(1e6)
    .updateMask(rice.riceMask.eq(1))
    .reduceRegion({
      reducer: ee.Reducer.sum(),
      geometry: base.geometry,
      scale: 375,
      maxPixels: 1e11,
      tileScale: 16
    })
    .getNumber('area');
  const nonRiceAreaKm2 = ee.Image.pixelArea()
    .divide(1e6)
    .updateMask(rice.riceMask.eq(0))
    .updateMask(base.cropMask)
    .reduceRegion({
      reducer: ee.Reducer.sum(),
      geometry: base.geometry,
      scale: 375,
      maxPixels: 1e11,
      tileScale: 16
    })
    .getNumber('area');

  const fireStatsByYear = years.map((year) => {
    const points = viirsWithClass.filter(ee.Filter.eq('anio', year));
    const riceDetections = points
      .filter(ee.Filter.eq('is_rice_cluster', 1))
      .size();
    const nonRiceDetections = points
      .filter(ee.Filter.eq('is_rice_cluster', 0))
      .size();
    const riceRate = ee.Number(riceDetections).divide(riceAreaKm2);
    const nonRiceRate = ee.Number(nonRiceDetections).divide(nonRiceAreaKm2);
    return ee.Feature(null, {
      anio: year,
      detecciones_arroz: riceDetections,
      detecciones_no_arroz: nonRiceDetections,
      area_arroz_km2: riceAreaKm2,
      area_no_arroz_km2: nonRiceAreaKm2,
      detecciones_arroz_por_km2: riceRate,
      detecciones_no_arroz_por_km2: nonRiceRate,
      arroz_supera_no_arroz: riceRate.gt(nonRiceRate)
    });
  });
  const fireStats = ee.FeatureCollection(fireStatsByYear);
  const yearsWithHigherRiceRate = fireStats
    .filter(ee.Filter.eq('arroz_supera_no_arroz', 1))
    .size();
  const summary = ee.Dictionary({
    anios_analizados: years.length,
    anios_con_mayor_tasa_en_arroz: yearsWithHigherRiceRate,
    conclusion: ee.Algorithms.If(
      yearsWithHigherRiceRate.eq(years.length),
      'Los resultados VIIRS respaldan la expectativa en los tres años.',
      ee.Algorithms.If(
        yearsWithHigherRiceRate.gt(0),
        'Los resultados VIIRS respaldan la expectativa solo parcialmente.',
        'Los resultados VIIRS no respaldan la expectativa durante 2017-2019.'
      )
    )
  });
  return {fireStats, summary, viirsWithClass};
}

async function runFullAnalysis() {
  const base = buildBaseAnalysis();
  const rice = buildRiceAnalysis(base);
  const fire = buildFireAnalysis(base, rice);

  const [clusterStats, fireStats, fireSummary, metadata] = await Promise.all([
    evaluate(rice.clusterStatsRanked),
    evaluate(fire.fireStats),
    evaluate(fire.summary),
    evaluate(ee.Dictionary({
      bellavista_features: base.selected.size(),
      training_samples: base.training.size(),
      alphaearth_bands: base.clusterImage.bandNames().size(),
      fire_points_in_cropland: fire.viirsWithClass.size(),
      clusters_con_mayoria_50pct: rice.majorityCount
    }))
  ]);

  writeJson('gee_analysis_results.json', {
    project: PROJECT,
    glorice_asset: GLORICE_ASSET,
    fire_asset: FIRE_ASSET,
    min_clusters: MIN_CLUSTERS,
    max_clusters: MAX_CLUSTERS,
    metadata,
    cluster_stats: clusterStats,
    fire_stats: fireStats,
    fire_summary: fireSummary
  });
}

async function main() {
  validateConfiguration();
  await authenticateAndInitialize();
  if (MODE === 'auth') {
    await checkAuthentication();
  } else if (MODE === 'check') {
    await checkAccess();
  } else if (MODE === 'prepare') {
    await prepareTraining();
  } else if (MODE === 'analyze') {
    await runFullAnalysis();
  } else {
    throw new Error(`Modo desconocido: ${MODE}. Usa auth, check, prepare o analyze.`);
  }
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
