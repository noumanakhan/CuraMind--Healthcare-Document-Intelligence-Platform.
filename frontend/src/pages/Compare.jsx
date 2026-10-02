import { COMPARE_ROWS } from '../data/mock.js'
import { IcDoc } from '../components/icons.jsx'

export default function Compare() {
  return (
    <div>
      <div className="cmp-picker">
        <div className="cmp-slot">
          <IcDoc width={16} height={16} />
          cardiology-consult-note.pdf
        </div>
        <div className="cmp-slot">
          <IcDoc width={16} height={16} />
          intake-form-amina-yusuf.pdf
        </div>
      </div>

      <table className="cmp-table">
        <thead>
          <tr>
            <th>Field</th>
            <th>cardiology-consult-note.pdf</th>
            <th>intake-form-amina-yusuf.pdf</th>
          </tr>
        </thead>
        <tbody>
          {COMPARE_ROWS.map((r, i) => (
            <tr key={i}>
              <td>{r[0]}</td>
              <td className={r[3] ? 'cmp-diff' : ''}>{r[1]}</td>
              <td className={r[3] ? 'cmp-diff' : ''}>{r[2]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
