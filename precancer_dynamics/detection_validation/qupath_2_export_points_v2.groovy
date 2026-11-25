/**
 * qupath_2_export_points.groovy
 * Exports one JSON per crop rectangle, in the same schema the browser counting
 * page produced, so analysis/manual_count/manual_recall.py can score it directly.
 *
 * Counts, for each crop rectangle (named as created by script 1):
 *   - every detection object whose centroid falls inside it (cell/nucleus detection), and
 *   - every point of any Points annotation inside it (your manual additions).
 * Duplicates closer than MIN_SEP_UM to an already-kept point are dropped.
 *
 * Set OUT_DIR to this folder before running.
 */
import groovy.json.JsonOutput
import qupath.lib.roi.interfaces.ROI

def OUT_DIR     = 'C:/Users/Administrator/Documents/AI_ML/Pancrea Cancer/NPJ SBA/analysis/manual_count/QuPath'
def TAG         = 'qupath_v2'      // output file: <cropname>_<TAG>.json
def MIN_SEP_UM  = 2.0           // drop a point this close to one already kept

def server = getCurrentServer()
def cal    = server.getPixelCalibration()
def mpp    = cal.hasPixelSizeMicrons() ? cal.getAveragedPixelSizeMicrons() : 0.5027
def minSep = MIN_SEP_UM / mpp

def rects = getAnnotationObjects().findAll { it.getROI()?.isArea() && it.getName() }
if (rects.isEmpty()) {
    // v2 fallback: unnamed crop rectangle -> take the largest area annotation, name it from the image
    def big = getAnnotationObjects().findAll { it.getROI()?.isArea() }.max { it.getROI().getArea() }
    if (big == null) { print 'No crop rectangle found.'; return }
    def nm = getProjectEntry()?.getImageName() ?: server.getMetadata().getName()
    big.setName(nm.replaceAll(/^crop_/, '').replaceAll(/\.png$/, ''))
    rects = [big]
}

def dets = getDetectionObjects()
def pointAnns = getAnnotationObjects().findAll { it.getROI() instanceof qupath.lib.roi.PointsROI }
// v2: hand-drawn nucleus outlines (unnamed area annotations) also count, by centroid
def handAreas = getAnnotationObjects().findAll { it.getROI()?.isArea() && !(it in rects) }

new File(OUT_DIR).mkdirs()
rects.each { rect ->
    def r = rect.getROI()
    def x0 = r.getBoundsX(), y0 = r.getBoundsY(), s = r.getBoundsWidth()
    def inside = { double x, double y -> x >= x0 && x < x0 + s && y >= y0 && y < y0 + s }

    def raw = []
    dets.each { d ->
        // prefer the nucleus ROI: with non-zero cell expansion the object ROI is
        // the expanded cell, whose centroid is shifted away from the nucleus.
        def c = (d instanceof qupath.lib.objects.PathCellObject && d.getNucleusROI() != null) ?
                 d.getNucleusROI() : d.getROI()
        if (inside(c.getCentroidX(), c.getCentroidY())) raw << [c.getCentroidX(), c.getCentroidY()]
    }
    handAreas.each { ha ->
        def c = ha.getROI()
        if (inside(c.getCentroidX(), c.getCentroidY())) raw << [c.getCentroidX(), c.getCentroidY()]
    }
    pointAnns.each { pa ->
        pa.getROI().getAllPoints().each { p ->
            if (inside(p.getX(), p.getY())) raw << [p.getX(), p.getY()]
        }
    }

    def kept = []
    raw.each { p ->
        if (!kept.any { Math.hypot(it[0] - p[0], it[1] - p[1]) < minSep }) kept << p
    }

    def label = rect.getName().contains('stroma') ? 'stroma' :
                rect.getName().contains('acinar') ? 'acinar' :
                rect.getName().contains('panin')  ? 'panin'  : 'unknown'
    def out = [
        name          : rect.getName(),
        slide         : rect.getName().split('_')[0],
        label         : label,
        x0            : x0 as int,
        y0            : y0 as int,
        size_px       : s as int,
        mpp           : mpp,
        source        : 'qupath',
        n_detections  : raw.size(),
        n_after_merge : kept.size(),
        points_crop_px: kept.collect { [ (it[0] - x0).round(1), (it[1] - y0).round(1) ] },
    ]
    def f = new File(OUT_DIR, "${rect.getName()}_${TAG}.json")
    f.text = JsonOutput.toJson(out)
    print "${rect.getName()}: ${raw.size()} raw -> ${kept.size()} kept  ->  ${f.getName()}"
}
print "mpp used: ${mpp}"
