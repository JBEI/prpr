getConnectionInfos = () ->
  wells = []
  connections = jsPlumb.getConnections()
  for element in connections
    src = element.sourceId
    dst = element.targetId
    source = src;
    if wells[source]
      wells[source].push(dst)
    else
      wells[source] = [dst]