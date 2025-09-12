import React, { useEffect, useRef } from 'react';

let Plotly: any;
if (typeof window !== 'undefined') {
  Plotly = require('plotly.js-dist-min');
}


function parseTxt(txt: string) {
  const lines = txt.split(/\r?\n/);
  const x: number[] = [];
  const y: number[] = [];
  for (const line of lines) {
    const parts = line.trim().split(/\s+/);
    if (parts.length >= 2 && !isNaN(Number(parts[0])) && !isNaN(Number(parts[1]))) {
      x.push(Number(parts[0]));
      y.push(Number(parts[1]));
    }
  }
  return { x, y };
}


export function PlotlyXASSpectraViewer({ txtContent, fileName }: { txtContent?: string | null, fileName?: string | null }) {
  const plotRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  // The file name to use as the plot title
  const plotTitle = fileName || 'XAS Spectra';

  useEffect(() => {
    const plotData = async (txt: string) => {
      setLoading(true);
      setError(null);
      try {
        const { x, y } = parseTxt(txt);
        if (plotRef.current && Plotly) {
          Plotly.newPlot(plotRef.current, [
            {
              x,
              y,
              mode: 'lines',
              type: 'scatter',
              name: 'μt',
              line: { color: '#1f77b4' },
            },
          ], {
            title: {
              text: plotTitle,
              font: { size: 22 },
              xref: 'paper',
              x: 0.5,
              xanchor: 'center',
            },
            xaxis: {
              title: {
                text: 'Energy [eV]',
                font: { size: 18 },
              },
              tickfont: { size: 14 },
            },
            yaxis: {
              title: {
                text: 'μt',
                font: { size: 18 },
              },
              tickfont: { size: 14 },
            },
            margin: { t: 60, l: 60, r: 20, b: 50 },
            plot_bgcolor: '#fff',
            paper_bgcolor: '#fff',
            autosize: true,
          }, { responsive: true });
        }
      } catch (err: any) {
        setError(err.message || 'Error loading plot');
      } finally {
        setLoading(false);
      }
    };

    if (txtContent) {
      plotData(txtContent);
    } else {
      // fallback to default file if no txtContent provided
      const fetchAndPlot = async () => {
        setLoading(true);
        setError(null);
        try {
          const resp = await fetch('/Cu-K_CuO_Si111_50ms_120613.txt');
          if (!resp.ok) throw new Error('Failed to fetch XAS txt file');
          const txt = await resp.text();
          await plotData(txt);
        } catch (err: any) {
          setError(err.message || 'Error loading plot');
        } finally {
          setLoading(false);
        }
      };
      fetchAndPlot();
    }
  }, [txtContent, plotTitle]);

  return (
    <div style={{ width: '100%', height: 400 }}>
      {loading && <div>Loading XAS data...</div>}
      {error && <div style={{color:'red'}}>Error: {error}</div>}
      <div ref={plotRef} style={{ width: '100%', height: '100%' }} />
    </div>
  );
}
