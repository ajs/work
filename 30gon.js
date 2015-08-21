function pairsof(a) {
    var pairs = [];
    var range = a.length;

    for (var i = 0; i < range; i++) {
	for (var j = i+1; j < range; j++) {
	    pairs.push([i,j]);
	}
    }
    return pairs;
}

// Pop item out of source and push it onto target.
// Return the shortened source list.
function stripinto(item, source, target) {
    var found = source.indexOf(item);
    if (found != -1) {
	target.push(item);
	var before = source.slice(0, found);
	var after = source.slice(found+1, source.length);
	return before.concat(after);
    }

    alert("Item not found!" + "source=" + JSON.stringify(source) + ", item="+ JSON.stringify(item) + ", target=" + JSON.stringify(target));
    return null;
}

function connect_nodes(path, radius, margin, verts, node1, node2) {
    var center_x = radius + margin;
    var center_y = radius + margin;
    var circum = Math.PI*2
    var angle_step = circum / verts;

    var angle1 = angle_step * node1;
    var angle2 = angle_step * node2;

    var x1 = center_x + radius * Math.sin(angle1);
    var y1 = center_y + radius * Math.cos(angle1);
    var x2 = center_x + radius * Math.sin(angle2);
    var y2 = center_y + radius * Math.cos(angle2);

    path.moveTo(x1, y1);
    path.lineTo(x2, y2);
}

function draw_connections(canvas, all) {
    var ctx = canvas.getContext('2d');
    var path = new Path2D;

    var radius=200;
    var margin=20;
    var verts = all.length;

    add_debug(all);

    function listinlist(l1, l2) {
	for (var i = 0; i < l2.length; i++) {
	    if (JSON.stringify(l1) == JSON.stringify(l2[i])) {
		return true;
	    }
	}
	return false;
    }

    for (var i = 0; i < verts; i+=2) {
	var trip = all[i];
	for (var j = 1; j < verts; j+=2) {
	    var pair = all[j];
	    var jtrip = JSON.stringify(all[i]);
	    var jpair = JSON.stringify(all[j]);
	    console.log("Connect all[" + i + "]=" + jtrip + " -> all[" + j + "]=" + jpair);
	    console.log("listinlist(" + jpair + ", " + jtrip + ") = " + listinlist(pair, trip));
	    if (!listinlist(pair, trip)) {
		continue;
	    }
	    connect_nodes(path, radius, margin, verts, i, j);
	}
    }

    ctx.lineWidth = 2;
    ctx.stroke(path);
}

function add_debug(all) {
    function debug_list(name, list) {
	msg = ""
	msg += "<h2>" + name + "</h2><ul>";
	for (var i = 0; i < list.length; i++) {
	    msg += "<li>" + JSON.stringify(list[i]) + "</li>";
	}
	msg += "</ul>";
	return msg;
    }

    var debug_info = "";
    var debug = document.getElementById('debug');
    debug_info += debug_list("all", all);
    debug.innerHTML = debug.innerHTML + debug_info;
}

function draw() {
    var canvas = document.getElementById('30gon');

    if (!canvas.getContext) {
	return;
    }

    all30 = [[[0, 1], [2, 3], [4, 5]],
	     [0, 1],
	     [[0, 1], [2, 4], [3, 5]],
	     [2, 4],
	     [[0, 3], [1, 5], [2, 4]],
	     [0, 3],
	     [[0, 3], [1, 2], [4, 5]],
	     [1, 2],
	     [[0, 5], [1, 2], [3, 4]],
	     [3, 4],
	     [[0, 1], [2, 5], [3, 4]],
	     [2, 5],
	     [[0, 3], [1, 4], [2, 5]],
	     [1, 4],
	     [[0, 2], [1, 4], [3, 5]],
	     [3, 5],
	     [[0, 4], [1, 2], [3, 5]],
	     [0, 4],
	     [[0, 4], [1, 3], [2, 5]],
	     [1, 3],
	     [[0, 5], [1, 3], [2, 4]],
	     [0, 5],
	     [[0, 5], [1, 4], [2, 3]],
	     [2, 3],
	     [[0, 4], [1, 5], [2, 3]],
	     [1, 5],
	     [[0, 2], [1, 5], [3, 4]],
	     [0, 2],
	     [[0, 2], [1, 3], [4, 5]],
	     [4, 5]];

    draw_connections(canvas, all30);
}
