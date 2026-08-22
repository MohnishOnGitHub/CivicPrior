import {
  categoryColor,
  schematicPosition,
  type MapPoint,
} from "@/lib/geoMap";

const WIDTH = 720;
const HEIGHT = 520;

export default function DistrictMap({
  points,
  activeId,
  onSelect,
}: {
  points: MapPoint[];
  activeId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <svg
      className="district-map"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label="Synthetic CivicPrior demo district. Coordinates are invented and not official."
    >
      <rect width={WIDTH} height={HEIGHT} fill="#eef3f0" />
      <ellipse cx="430" cy="268" rx="250" ry="210" fill="#d9e4dc" />
      <ellipse cx="390" cy="268" rx="168" ry="142" fill="#c9d8cf" />
      <ellipse cx="368" cy="268" rx="92" ry="78" fill="#b7c8bf" />
      <ellipse cx="180" cy="300" rx="150" ry="170" fill="#e4ebe3" />

      <text x="368" y="262" className="district-label" textAnchor="middle">
        Urban core
      </text>
      <text x="500" y="150" className="district-label" textAnchor="middle">
        Peri-urban ring
      </text>
      <text x="150" y="150" className="district-label" textAnchor="middle">
        Rural west
      </text>
      <text x="620" y="250" className="district-label" textAnchor="middle">
        East edge
      </text>
      <text x="360" y="28" className="district-title" textAnchor="middle">
        CivicPrior demo district · invented layout
      </text>
      <text x="48" y="36" className="district-compass">
        N
      </text>
      <line x1="52" y1="42" x2="52" y2="62" stroke="#3d4d5f" strokeWidth="1.5" />

      {points.map((point) => {
        const { x, y } = schematicPosition(point, WIDTH, HEIGHT);
        const fill = categoryColor(point.category);
        const radius = point.high_demand ? 13 : 10;
        const active = activeId === point.id;
        return (
          <g
            key={point.id}
            className="map-marker"
            transform={`translate(${x} ${y})`}
            onClick={() => onSelect(point.id)}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelect(point.id);
              }
            }}
          >
            {point.underserved ? (
              <circle r={radius + 7} fill="none" stroke="#b45309" strokeWidth="3" />
            ) : null}
            <circle
              r={radius}
              fill={point.selected ? fill : "#fffdf8"}
              stroke={fill}
              strokeWidth={point.selected ? 3 : 2}
              strokeDasharray={point.selected ? undefined : "3 2"}
              opacity={point.unmatched ? 0.85 : 1}
            />
            {point.severe_deficit ? (
              <rect x="-3" y="-3" width="6" height="6" fill="#8a3419" />
            ) : (
              <circle r="2.4" fill={point.selected ? "#fffdf8" : fill} />
            )}
            {active ? (
              <circle r={radius + 11} fill="none" stroke="#132033" strokeWidth="1.5" />
            ) : null}
            <text y={radius + 14} textAnchor="middle" className="marker-label">
              {point.location}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
