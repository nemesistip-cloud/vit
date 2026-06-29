import React, { useState, useEffect } from 'react';
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker
} from 'react-simple-maps';
import { explorerApi } from '../api/client';
import { MapPin } from 'lucide-react';

const geoUrl = "https://raw.githubusercontent.com/lotusms/world-map-data/master/world-110m.json";

export default function NodeMap() {
  const [nodes, setNodes] = useState([]);

  useEffect(() => {
    explorerApi.getNodesMap().then(data => {
      setNodes(data.nodes || []);
    });
  }, []);

  return (
    <div className="bg-[#121826] border border-[#1F2937] rounded-lg p-4 relative">
      <h2 className="text-white font-BarlowCondensed font-bold text-xl mb-4 flex items-center">
        <MapPin size={20} className="mr-2 text-purple-500" />
        Global Node Distribution
      </h2>
      <div className="h-[400px] w-full">
        <ComposableMap projectionConfig={{ scale: 150 }}>
          <Geographies geography={geoUrl}>
            {({ geographies }) =>
              geographies.map((geo) => (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  fill="#0A0E1A"
                  stroke="#1F2937"
                />
              ))
            }
          </Geographies>
          {nodes.map(({ lat, lng, node_type, node_id }) => (
            <Marker key={node_id} coordinates={[lng, lat]}>
              <circle
                r={3}
                fill={node_type === 'validator' ? '#8B5CF6' : '#00E676'}
                className="animate-pulse"
              />
            </Marker>
          ))}
        </ComposableMap>
      </div>
      <div className="absolute bottom-4 left-4 flex space-x-4">
        <div className="flex items-center text-xs text-gray-400">
          <div className="w-2 h-2 rounded-full bg-green-500 mr-2" /> Storage Node
        </div>
        <div className="flex items-center text-xs text-gray-400">
          <div className="w-2 h-2 rounded-full bg-purple-500 mr-2" /> Validator Node
        </div>
      </div>
    </div>
  );
}
