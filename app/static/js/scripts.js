function createNetwork(graph) {

    // Template aus HTML holen und kompilieren
    const popup_source = document.getElementById('popup-template').innerHTML;
    const popup_template = Handlebars.compile(popup_source);


    // Netzwerk-Container
    const nodes = new vis.DataSet(graph.nodes)
     
    // Kanten
    const edges = new vis.DataSet(graph.edges);


    //Physics
    const physics_base = {
        enabled: true
    };

    const physics_forceAtlas2Based = {
        enabled: true,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          springLength: 150, // Längere Feder für größere Abstände
          springConstant: 0.01, // Geringere Federkonstante für san
        },
        stabilization: {
          iterations: 200
        }
    };

    // Konfiguration
    const container = document.getElementById('network');
    const data = {
      nodes: nodes,
      edges: edges
    };
    const options = {
      nodes: {
        shapeProperties: {
          useImageSize: false, // Nutzt Originalgröße des SVGs
        },
        size: 15,
        font: {
          size: 12
        }
      },
      edges: {
        arrows: {
          to: { enabled: true, scaleFactor: 0.6 }
        },
        font: {
          size: 10,        // kleinere Schrift für Edges
          align: 'middle'
        }
      },
      physics: physics_base
    };

    // Netzwerk erstellen
    const network = new vis.Network(container, data, options);


    network.on("dragEnd", function (params) {
      if (params.nodes.length > 0) {
        const id = params.nodes[0];
        const pos = network.getPositions([id]);
        console.log(`Knoten ${id} neue Position:`, pos[id]);
      }
    });


    network.on("click", function (params) {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const nodeData = nodes.get(nodeId);
        const pointer = params.pointer.DOM;
      

        //Popup rendern
        const html = popup_template(nodeData.user_data);

        // Popup anzeigen
        $('#popup')
          .html(html)
          .css({
            left: pointer.x + 'px',
            top: pointer.y + 'px',
            display: 'block'
        });

        // Toggle für Klassenhierarchie
        $(document).on("click", ".toggle-class-hierarchy", function () {
          $(this).next(".class-hierarchy").slideToggle(200);
        });

      } else {
        $('#popup').hide(); // Kein Knoten angeklickt
      }
    });

   
    // Leeren (optional)
    $('#viewSelector').empty();

    // Optionen hinzufügen
    $.each(graph.views, function(key, label) {
      $('#viewSelector').append(
        $('<option>', {
          value: key,
          text: label
        })
      );
    });


    $('#viewSelector').on('change', function () {
      view = $(this).val();
      console.log("View changed to: " + view);
      
      nodes.get().forEach(function (node) {
        if (node.user_data?.views.includes(view)) {
          nodes.update({ id: node.id, hidden: false });
        } else {
          nodes.update({ id: node.id, hidden: true });
        }
      });
    });


    $("#makeCluster").on("click", function () {
      console.log("ClusterTest button clicked");
      network.cluster({
        joinCondition: function (node) {
          // Alle Knoten mit id > 2 clustern
          return node.id > 2;
        },
        clusterNodeProperties: {
          id: "cluster1",
          label: "Gruppe A",
          shape: "box",
          color: { background: "lightblue", border: "blue" },
          borderWidth: 3
        }
      });
    });
    
    $("#clearCluster").on("click", function () {
      network.openCluster("cluster1");
    })

}

function init() {
    $(document).on('click', function (e) {
      // Wenn Klick außerhalb von Popup UND außerhalb des Netzwerks
      if (
        !$(e.target).closest('#popup').length &&
        !$(e.target).closest('#network').length
      ) {
        $('#popup').hide();
      }
  });

 
}

function loadGraph(projectId) {

    init();

    // API Call mit getJSON
    $.getJSON('/graph/'+projectId, function(data) {
        console.log(data);
        // Netzwerk aufbauen
        createNetwork(data);

    }).fail(function(jqxhr, textStatus, error) {
        console.log("Error: " + textStatus + ", " + error);
    });

}




   