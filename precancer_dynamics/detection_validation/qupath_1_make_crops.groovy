/**
 * qupath_1_make_crops.groovy
 * Creates the 256x256 crop rectangles (level-0 pixels) for the slide that is
 * currently open, so nucleus detection can be restricted to exactly the regions
 * that were counted by hand.
 *
 * Run: Automate > Script editor > paste > Run.
 */
import qupath.lib.objects.PathObjects
import qupath.lib.roi.ROIs
import qupath.lib.regions.ImagePlane

def CROPS = [
    [name:'M4_stroma_x16768_y7424',  slide:'M4', label:'stroma', x0:16768, y0:7424,  size:256],
    [name:'M4_acinar_x19840_y20864', slide:'M4', label:'acinar', x0:19840, y0:20864, size:256],
    [name:'F8_panin_x2432_y11648',   slide:'F8', label:'panin',  x0:2432,  y0:11648, size:256],
]

def imageName = getCurrentServer().getMetadata().getName()
print "Open image: ${imageName}"

def plane = ImagePlane.getDefaultPlane()
def added = []
CROPS.each { c ->
    // match the slide by its tag appearing in the file name (M4, F8, ...)
    if (!(imageName =~ /(?i)(^|[^A-Za-z])${c.slide}([^0-9]|$)/)) return
    def roi = ROIs.createRectangleROI(c.x0, c.y0, c.size, c.size, plane)
    def ann = PathObjects.createAnnotationObject(roi)
    ann.setName(c.name)
    addObject(ann)
    added << c.name
}
if (added.isEmpty())
    print "No crop matches this slide. Expected one of: " + CROPS.collect{it.slide}.unique()
else
    print "Added ${added.size()} crop rectangle(s): ${added}"
fireHierarchyUpdate()
