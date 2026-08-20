import type { CompactProject } from "@/lib/types";
import { formatCr, formatImpact } from "@/lib/format";

export function ProjectTable({
  projects,
  empty = "No projects",
}: {
  projects: CompactProject[];
  empty?: string;
}) {
  if (!projects.length) {
    return <p className="muted">{empty}</p>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Project</th>
            <th>Location</th>
            <th>Category</th>
            <th>Need</th>
            <th>Impact</th>
            <th>Equity</th>
            <th>Underserved</th>
            <th>Cost</th>
          </tr>
        </thead>
        <tbody>
          {projects.map((project) => (
            <tr key={project.id}>
              <td>{project.id}</td>
              <td>{project.name}</td>
              <td>{project.location}</td>
              <td>{project.category}</td>
              <td>{project.need_score.toFixed(2)}</td>
              <td>{formatImpact(project.expected_impact)}</td>
              <td>{project.equity.toFixed(1)}</td>
              <td>
                <span className={`badge ${project.underserved ? "yes" : "no"}`}>
                  {project.underserved ? "yes" : "no"}
                </span>
              </td>
              <td>{formatCr(project.cost_cr)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
