// Function to get the dynamic window size
function getWindowSize() {
    return { width: window.innerWidth, height: window.innerHeight };
}

// Function to extract artist names from their URLs
function extractArtistName(url) {
    if (!url) return "Unknown";
    let lastSegment = url.substring(url.lastIndexOf('/') + 1);
    let name = lastSegment.split('.')[0];
    return name.replace(/_/g, ' ').trim();
}

// Function to process CSV file after upload
function processCSV(file) {
    const reader = new FileReader();
    reader.onload = function (event) {
        const csvData = d3.csvParse(event.target.result);
        initializeNetwork(csvData);
    };
    reader.readAsText(file);
}

// Function to initialize the network visualization
function initializeNetwork(data) {
    let allNodes = [];
    let allLinks = [];

    // Extract unique labels dynamically
    const labels = [...new Set(data.map(d => d.Label))];

    // Extract unique entities based on labels
    const entities = {};
    labels.forEach(label => {
        entities[label] = [...new Set(data.filter(d => d.Label === label).map(d => d.Entity))];
    });

    const artists = [...new Set(data.map(d => d.Link))];

    // Create initial nodes (Artists only at the beginning)
    allNodes = artists.map(d => ({ id: extractArtistName(d), type: "Artist", url: d }));

    // Create artist-entity links dynamically
    allLinks = data.map(row => ({
        source: extractArtistName(row.Link),
        target: row.Entity,
        type: row.Label
    }));

    // Get window size
    let { width, height } = getWindowSize();

    // Define color scale
    const color = d3.scaleOrdinal()
        .domain(["Artist", ...labels])
        .range(d3.schemeCategory10);

    // Create SVG container with zoom and pan
    const svg = d3.select("#network-svg")
        .attr("width", width)
        .attr("height", height)
        .call(d3.zoom().scaleExtent([0.1, 4]).on("zoom", (event) => {
            g.attr("transform", event.transform);
        }))
        .append("g");

    // Create main group
    const g = svg.append("g");

    // Initialize force simulation
    const simulation = d3.forceSimulation()
        .force("link", d3.forceLink().id(d => d.id).distance(150))
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2));

    let link = g.append("g")
        .attr("stroke", "#aaa")
        .attr("stroke-opacity", 0.6)
        .selectAll("line");

    let node = g.append("g")
        .selectAll("g");

    // Function to update visualization based on selected filters
    function updateVisualization() {
        const filterEntity = document.getElementById("filter-type2").value;

        let visibleNodes = [...allNodes];
        let visibleLinks = [];

        if (filterEntity !== "None") {
            visibleLinks = allLinks.filter(l => l.type === filterEntity);

            const entityIds = new Set(visibleLinks.map(l => l.target));
            const relatedEntities = entities[filterEntity]
                .filter(entity => entityIds.has(entity))
                .map(entity => ({ id: entity, type: filterEntity }));

            visibleNodes = [...allNodes, ...relatedEntities];
        }

        simulation.nodes(visibleNodes);
        simulation.force("link").links(visibleLinks);
        simulation.alpha(1).restart();

        link = link
            .data(visibleLinks, d => `${d.source}-${d.target}`)
            .join(
                enter => enter.append("line")
                    .attr("stroke-width", 3),
                update => update,
                exit => exit.remove()
            );

        node = node
            .data(visibleNodes, d => d.id)
            .join(
                enter => {
                    const g = enter.append("g")
                        .call(d3.drag()
                            .on("start", (event, d) => {
                                if (!event.active) simulation.alphaTarget(0.3).restart();
                                d.fx = d.x;
                                d.fy = d.y;
                                if (d.type === "Artist") {
                                    highlightArtist(d);
                                }
                            })
                            .on("drag", (event, d) => {
                                d.fx = event.x;
                                d.fy = event.y;
                            })
                            .on("end", (event, d) => {
                                if (!event.active) simulation.alphaTarget(0);
                                d.fx = null;
                                d.fy = null;
                                if (d.type === "Artist") {
                                    restoreNodes();
                                }
                            })
                        )
                        .on("click", (event, d) => {
                            if (d.type === "Artist" && d.url) {
                                window.open(d.url, "_blank");
                            }
                        });

                    g.append("circle")
                        .attr("r", 14)
                        .attr("fill", d => color(d.type))
                        .attr("class", "node-circle");

                    g.append("text")
                        .attr("x", 16)
                        .attr("y", "0.31em")
                        .text(d => d.id);

                    return g;
                },
                update => update,
                exit => exit.remove()
            );

        simulation.on("tick", () => {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node.attr("transform", d => `translate(${d.x},${d.y})`);
        });
    }

        // Function to show only linked targets and hide unrelated nodes while dragging an artist
    function highlightArtist(artistNode) {
        const linkedTargets = new Set();
        linkedTargets.add(artistNode.id); // Keep the artist node visible

        // Find all target nodes directly linked to the artist
        allLinks.forEach(l => {
            if (l.source.id === artistNode.id) {
                linkedTargets.add(l.target.id);
            }
        });

        // Hide all other artist nodes except the current artist and its targets
        d3.selectAll(".node-circle")
            .style("opacity", d => linkedTargets.has(d.id) ? 1 : 0);

        d3.selectAll("text")
            .style("opacity", d => linkedTargets.has(d.id) ? 1 : 0);

        // Show only links that connect to the artist node
        d3.selectAll("line")
            .style("opacity", d => (d.source.id === artistNode.id) ? 1 : 0);
    }

    // Restore all nodes and links after drag stops
    function restoreNodes() {
        d3.selectAll(".node-circle").style("opacity", 1);
        d3.selectAll("text").style("opacity", 1);
        d3.selectAll("line").style("opacity", 1);
    }

    // Populate dropdowns dynamically
    const relationDropdown = document.getElementById("filter-type2");
    relationDropdown.innerHTML = "";
    ["None", ...labels].forEach(type => {
        const option = document.createElement("option");
        option.value = type;
        option.textContent = type;
        relationDropdown.appendChild(option);
    });

    relationDropdown.addEventListener("change", updateVisualization);
    updateVisualization();
}

// Event listener for file upload
document.getElementById("file-upload").addEventListener("change", function (event) {
    const file = event.target.files[0];
    if (file) {
        processCSV(file);
    }
});
