/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useState } from 'react';
import {
  addHoClass, addHoEntity, addHoParameter, addHoRole, addHoPosition,
  createHoInstance, getCars, getEnumerations, getEnumerationValues,
  getHoClasses, getHoEntities, getHoInstances, getHoParameters, getHoRoles,
  getHoClassSchema, getUnits, linkHoParameter, linkHoRole, setHoActor, setHoParameter,
} from '../../api/client';

const pageStyle = { fontFamily: '"Inter Tight", sans-serif', color: '#1C1C19', marginTop: 34 };
const panelStyle = { background: '#FFFFFF', border: '1px solid rgba(28,28,25,.22)', borderRadius: 12, padding: 22, minWidth: 0 };
const inputStyle = { width: '100%', boxSizing: 'border-box', padding: '10px 12px', border: '1px solid #B8B8B4', borderRadius: 8, font: 'inherit', background: '#fff', minHeight: 40 };
const buttonStyle = { border: '1px solid #1C1C19', borderRadius: 8, padding: '10px 14px', background: '#1C1C19', color: '#fff', cursor: 'pointer', font: 'inherit', minHeight: 40 };
const secondaryButtonStyle = { ...buttonStyle, background: '#fff', color: '#1C1C19' };

const Field = ({ label, children }) => (
  <label style={{ display: 'flex', flexDirection: 'column', gap: 7, fontSize: 14, fontWeight: 500 }}>
    {label}{children}
  </label>
);
const SectionTitle = ({ children }) => <h2 style={{ margin: '0 0 18px', fontSize: 21, fontWeight: 600 }}>{children}</h2>;
const FormGrid = ({ children }) => <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 14, alignItems: 'end' }}>{children}</div>;

const OperationsPage = () => {
  const [classes, setClasses] = useState([]);
  const [entities, setEntities] = useState([]);
  const [roles, setRoles] = useState([]);
  const [parameters, setParameters] = useState([]);
  const [cars, setCars] = useState([]);
  const [units, setUnits] = useState([]);
  const [enumerations, setEnumerations] = useState([]);
  const [instances, setInstances] = useState([]);
  const [classSchema, setClassSchema] = useState({ parameters: [], roles: [] });
  const [selectedClassId, setSelectedClassId] = useState('');
  const [activeOperationId, setActiveOperationId] = useState('');
  const [enumValues, setEnumValues] = useState([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  const [classForm, setClassForm] = useState({ name: '', code: '', parent_id: '' });
  const [entityForm, setEntityForm] = useState({ name: '', inn: '', entity_type: 'legal' });
  const [roleForm, setRoleForm] = useState({ name: '', code: '' });
  const [parameterForm, setParameterForm] = useState({ code: '', name: '', value_type: 'string', unit_id: '', enum_id: '' });
  const [linkParameterForm, setLinkParameterForm] = useState({ id_param: '', is_required: false });
  const [linkRoleForm, setLinkRoleForm] = useState({ id_role: '', is_required: true });
  const [operationForm, setOperationForm] = useState({ doc_number: '', doc_date: '', total_amount: '0' });
  const [actorForm, setActorForm] = useState({ id_role: '', id_sxd: '' });
  const [operationParameterForm, setOperationParameterForm] = useState({ id_param: '', value: '', enum_value_id: '' });
  const [positionForm, setPositionForm] = useState({ id_car: '', quantity: '1', price: '' });

  const refresh = useCallback(async () => {
    setError('');
    try {
      const [classData, entityData, roleData, parameterData, carData, unitData, enumData, instanceData] = await Promise.all([
        getHoClasses(), getHoEntities(), getHoRoles(), getHoParameters(),
        getCars(), getUnits(), getEnumerations(), getHoInstances(),
      ]);
      setClasses(classData.classes || []);
      setEntities(entityData.entities || []);
      setRoles(roleData.roles || []);
      setParameters(parameterData.parameters || []);
      setCars(carData.cars || []);
      setUnits(unitData.units || []);
      setEnumerations(enumData.enumerations || []);
      setInstances(instanceData.instances || []);
      setSelectedClassId((current) => current || String(classData.classes?.[0]?.id_ho_class || ''));
      setActiveOperationId((current) => current || String(instanceData.instances?.[0]?.ho?.id_ho || ''));
    } catch (e) {
      setError(typeof e === 'string' ? e : e?.message || 'Не удалось загрузить данные. Проверьте, запущен ли Flask-сервер.');
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    if (!selectedClassId) {
      setClassSchema({ parameters: [], roles: [] });
      return;
    }
    getHoClassSchema(selectedClassId)
      .then(setClassSchema)
      .catch(() => setClassSchema({ parameters: [], roles: [] }));
  }, [selectedClassId, classes, roles, parameters]);

  const selectedOperation = instances.find((item) => String(item.ho.id_ho) === String(activeOperationId));
  const selectedParameter = parameters.find((item) => String(item.id_param) === String(operationParameterForm.id_param));

  useEffect(() => {
    if (selectedOperation?.ho?.id_ho_class) {
      setSelectedClassId(String(selectedOperation.ho.id_ho_class));
    }
  }, [selectedOperation?.ho?.id_ho, selectedOperation?.ho?.id_ho_class]);

  useEffect(() => {
    if (selectedParameter?.value_type === 'enum' && selectedParameter.enum_id) {
      getEnumerationValues(selectedParameter.enum_id)
        .then((data) => setEnumValues(data.values || []))
        .catch(() => setEnumValues([]));
    } else {
      setEnumValues([]);
    }
    setOperationParameterForm((current) => ({ ...current, enum_value_id: '' }));
  }, [selectedParameter?.id_param, selectedParameter?.enum_id, selectedParameter?.value_type]);

  const runAction = async (action, successMessage) => {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const result = await action();
      setNotice(successMessage);
      await refresh();
      return result;
    } catch (e) {
      setError(typeof e === 'string' ? e : e?.message || 'Не удалось выполнить операцию');
      return null;
    } finally {
      setBusy(false);
    }
  };

  const handleCreateClass = async (event) => {
    event.preventDefault();
    const result = await runAction(() => addHoClass({ ...classForm, parent_id: classForm.parent_id || null }), 'Класс хозяйственной операции создан.');
    if (result) {
      setClassForm({ name: '', code: '', parent_id: '' });
      if (result.id_ho_class) setSelectedClassId(String(result.id_ho_class));
    }
  };
  const handleCreateEntity = async (event) => {
    event.preventDefault();
    const result = await runAction(() => addHoEntity(entityForm), 'Субъект хозяйственной деятельности добавлен.');
    if (result) setEntityForm({ name: '', inn: '', entity_type: 'legal' });
  };
  const handleCreateRole = async (event) => {
    event.preventDefault();
    const result = await runAction(() => addHoRole(roleForm), 'Роль добавлена.');
    if (result) setRoleForm({ name: '', code: '' });
  };
  const handleCreateParameter = async (event) => {
    event.preventDefault();
    const payload = { ...parameterForm, unit_id: parameterForm.unit_id || null, enum_id: parameterForm.value_type === 'enum' ? (parameterForm.enum_id || null) : null };
    const result = await runAction(() => addHoParameter(payload), 'Параметр хозяйственной операции создан.');
    if (result) setParameterForm({ code: '', name: '', value_type: 'string', unit_id: '', enum_id: '' });
  };
  const handleLinkParameter = async (event) => {
    event.preventDefault();
    if (!selectedClassId) return;
    const result = await runAction(() => linkHoParameter(selectedClassId, { ...linkParameterForm, id_param: Number(linkParameterForm.id_param) }), 'Параметр привязан к классу операции.');
    if (result) setLinkParameterForm({ id_param: '', is_required: false });
  };
  const handleLinkRole = async (event) => {
    event.preventDefault();
    if (!selectedClassId) return;
    const result = await runAction(() => linkHoRole(selectedClassId, { ...linkRoleForm, id_role: Number(linkRoleForm.id_role) }), 'Роль привязана к классу операции.');
    if (result) setLinkRoleForm({ id_role: '', is_required: true });
  };
  const handleCreateOperation = async (event) => {
    event.preventDefault();
    if (!selectedClassId) return;
    const result = await runAction(() => createHoInstance({
      id_ho_class: Number(selectedClassId),
      doc_number: operationForm.doc_number,
      doc_date: operationForm.doc_date || null,
      total_amount: operationForm.total_amount || 0,
    }), 'Хозяйственная операция создана.');
    if (result?.id_ho) setActiveOperationId(String(result.id_ho));
    if (result) setOperationForm({ doc_number: '', doc_date: '', total_amount: '0' });
  };
  const handleSetActor = async (event) => {
    event.preventDefault();
    if (!activeOperationId) return;
    const result = await runAction(() => setHoActor(activeOperationId, { id_role: Number(actorForm.id_role), id_sxd: Number(actorForm.id_sxd) }), 'Участник операции сохранён.');
    if (result) setActorForm({ id_role: '', id_sxd: '' });
  };
  const handleSetParameter = async (event) => {
    event.preventDefault();
    if (!activeOperationId || !selectedParameter) return;
    const payload = selectedParameter.value_type === 'enum'
      ? { id_param: Number(selectedParameter.id_param), enum_value_id: Number(operationParameterForm.enum_value_id) }
      : { id_param: Number(selectedParameter.id_param), value: operationParameterForm.value };
    const result = await runAction(() => setHoParameter(activeOperationId, payload), 'Параметр операции сохранён.');
    if (result) setOperationParameterForm((current) => ({ ...current, value: '', enum_value_id: '' }));
  };
  const handleAddPosition = async (event) => {
    event.preventDefault();
    if (!activeOperationId) return;
    const result = await runAction(() => addHoPosition(activeOperationId, {
      id_car: Number(positionForm.id_car),
      quantity: Number(positionForm.quantity),
      price: positionForm.price === '' ? null : Number(positionForm.price),
    }), 'Позиция добавлена, сумма операции пересчитана.');
    if (result) setPositionForm({ id_car: '', quantity: '1', price: '' });
  };

  const cardStyle = { ...panelStyle, marginBottom: 18 };
  const availableClassParameters = classSchema.parameters || [];
  const availableClassRoles = classSchema.roles || [];

  return (
    <div style={pageStyle}>
      <h1 style={{ margin: '0 0 10px', fontSize: 30, fontWeight: 600 }}>Хозяйственные операции</h1>
      <p style={{ margin: '0 0 24px', fontSize: 16, lineHeight: 1.5, maxWidth: 850, color: '#555550' }}>
        Создание типов операций, настройка параметров и ролей участников, оформление документов и добавление автомобилей в позиции операции.
      </p>
      {error && <div role="alert" style={{ padding: 14, marginBottom: 14, borderRadius: 8, background: '#FCE8E6', color: '#8A1C13' }}>{error}</div>}
      {notice && <div role="status" style={{ padding: 14, marginBottom: 14, borderRadius: 8, background: '#E7F4E4', color: '#245A20' }}>{notice}</div>}

      <section style={cardStyle}>
        <SectionTitle>1. Типы хозяйственных операций</SectionTitle>
        <form onSubmit={handleCreateClass}>
          <FormGrid>
            <Field label="Название типа"><input style={inputStyle} required value={classForm.name} onChange={(e) => setClassForm({ ...classForm, name: e.target.value })} placeholder="Например, Передача автомобиля" /></Field>
            <Field label="Код"><input style={inputStyle} required value={classForm.code} onChange={(e) => setClassForm({ ...classForm, code: e.target.value })} placeholder="CAR_TRANSFER" /></Field>
            <Field label="Родительский тип (необязательно)"><select style={inputStyle} value={classForm.parent_id} onChange={(e) => setClassForm({ ...classForm, parent_id: e.target.value })}><option value="">Без родителя</option>{classes.map((item) => <option key={item.id_ho_class} value={item.id_ho_class}>{item.name}</option>)}</select></Field>
            <button style={buttonStyle} disabled={busy}>Создать тип</button>
          </FormGrid>
        </form>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 18 }}>
          {classes.map((item) => <button key={item.id_ho_class} type="button" onClick={() => setSelectedClassId(String(item.id_ho_class))} style={{ ...secondaryButtonStyle, background: String(item.id_ho_class) === String(selectedClassId) ? '#E8E8E2' : '#fff' }}>{item.name} ({item.code})</button>)}
          {!classes.length && <span style={{ color: '#777' }}>Типов пока нет — создайте первый выше.</span>}
        </div>
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 18, alignItems: 'start' }}>
        <section style={panelStyle}>
          <SectionTitle>2. Субъекты деятельности</SectionTitle>
          <form onSubmit={handleCreateEntity}>
            <div style={{ display: 'grid', gap: 12 }}>
              <Field label="Название"><input style={inputStyle} required value={entityForm.name} onChange={(e) => setEntityForm({ ...entityForm, name: e.target.value })} /></Field>
              <Field label="ИНН (необязательно)"><input style={inputStyle} value={entityForm.inn} onChange={(e) => setEntityForm({ ...entityForm, inn: e.target.value })} inputMode="numeric" /></Field>
              <Field label="Тип субъекта"><select style={inputStyle} value={entityForm.entity_type} onChange={(e) => setEntityForm({ ...entityForm, entity_type: e.target.value })}><option value="legal">Юридическое лицо</option><option value="individual">Физическое лицо</option><option value="department">Подразделение</option></select></Field>
              <button style={buttonStyle} disabled={busy}>Добавить субъекта</button>
            </div>
          </form>
          <p style={{ marginBottom: 0, color: '#777', fontSize: 14 }}>Всего субъектов: {entities.length}</p>
        </section>

        <section style={panelStyle}>
          <SectionTitle>3. Роли участников</SectionTitle>
          <form onSubmit={handleCreateRole}>
            <div style={{ display: 'grid', gap: 12 }}>
              <Field label="Название роли"><input style={inputStyle} required value={roleForm.name} onChange={(e) => setRoleForm({ ...roleForm, name: e.target.value })} placeholder="Например, Получатель" /></Field>
              <Field label="Код"><input style={inputStyle} required value={roleForm.code} onChange={(e) => setRoleForm({ ...roleForm, code: e.target.value })} placeholder="RECIPIENT" /></Field>
              <button style={buttonStyle} disabled={busy}>Добавить роль</button>
            </div>
          </form>
          <p style={{ marginBottom: 0, color: '#777', fontSize: 14 }}>Всего ролей: {roles.length}</p>
        </section>

        <section style={panelStyle}>
          <SectionTitle>4. Параметры операций</SectionTitle>
          <form onSubmit={handleCreateParameter}>
            <div style={{ display: 'grid', gap: 12 }}>
              <Field label="Код"><input style={inputStyle} required value={parameterForm.code} onChange={(e) => setParameterForm({ ...parameterForm, code: e.target.value })} placeholder="DOC_AMOUNT" /></Field>
              <Field label="Название"><input style={inputStyle} required value={parameterForm.name} onChange={(e) => setParameterForm({ ...parameterForm, name: e.target.value })} /></Field>
              <Field label="Тип значения"><select style={inputStyle} value={parameterForm.value_type} onChange={(e) => setParameterForm({ ...parameterForm, value_type: e.target.value })}><option value="string">Строка</option><option value="numeric">Число</option><option value="integer">Целое число</option><option value="datetime">Дата и время</option><option value="enum">Перечисление</option></select></Field>
              <Field label="Единица измерения"><select style={inputStyle} value={parameterForm.unit_id} onChange={(e) => setParameterForm({ ...parameterForm, unit_id: e.target.value })}><option value="">Не выбрана</option>{units.map((unit) => <option key={unit.id_ei} value={unit.id_ei}>{unit.name} ({unit.short_name})</option>)}</select></Field>
              {parameterForm.value_type === 'enum' && <Field label="Перечисление"><select style={inputStyle} required value={parameterForm.enum_id} onChange={(e) => setParameterForm({ ...parameterForm, enum_id: e.target.value })}><option value="">Выберите справочник</option>{enumerations.map((item) => <option key={item.id_enum} value={item.id_enum}>{item.name}</option>)}</select></Field>}
              <button style={buttonStyle} disabled={busy}>Создать параметр</button>
            </div>
          </form>
          <p style={{ marginBottom: 0, color: '#777', fontSize: 14 }}>Всего параметров: {parameters.length}</p>
        </section>
      </div>

      <section style={{ ...cardStyle, marginTop: 18 }}>
        <SectionTitle>5. Настройка выбранного типа операции</SectionTitle>
        <Field label="Тип операции"><select style={inputStyle} value={selectedClassId} onChange={(e) => setSelectedClassId(e.target.value)}><option value="">Выберите тип операции</option>{classes.map((item) => <option key={item.id_ho_class} value={item.id_ho_class}>{item.name} ({item.code})</option>)}</select></Field>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 22, marginTop: 20 }}>
          <form onSubmit={handleLinkParameter} style={{ display: 'grid', gap: 12 }}>
            <h3 style={{ margin: 0, fontSize: 17 }}>Привязать параметр</h3>
            <Field label="Параметр"><select style={inputStyle} required value={linkParameterForm.id_param} onChange={(e) => setLinkParameterForm({ ...linkParameterForm, id_param: e.target.value })}><option value="">Выберите параметр</option>{parameters.map((item) => <option key={item.id_param} value={item.id_param}>{item.name} ({item.code})</option>)}</select></Field>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}><input type="checkbox" checked={linkParameterForm.is_required} onChange={(e) => setLinkParameterForm({ ...linkParameterForm, is_required: e.target.checked })} />Обязательный параметр</label>
            <button style={secondaryButtonStyle} disabled={busy || !selectedClassId}>Привязать параметр</button>
          </form>
          <form onSubmit={handleLinkRole} style={{ display: 'grid', gap: 12 }}>
            <h3 style={{ margin: 0, fontSize: 17 }}>Привязать роль</h3>
            <Field label="Роль"><select style={inputStyle} required value={linkRoleForm.id_role} onChange={(e) => setLinkRoleForm({ ...linkRoleForm, id_role: e.target.value })}><option value="">Выберите роль</option>{roles.map((item) => <option key={item.id_role} value={item.id_role}>{item.name} ({item.code})</option>)}</select></Field>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}><input type="checkbox" checked={linkRoleForm.is_required} onChange={(e) => setLinkRoleForm({ ...linkRoleForm, is_required: e.target.checked })} />Обязательная роль</label>
            <button style={secondaryButtonStyle} disabled={busy || !selectedClassId}>Привязать роль</button>
          </form>
          <div>
            <h3 style={{ margin: '0 0 10px', fontSize: 17 }}>Схема выбранного типа</h3>
            <div style={{ fontSize: 14, lineHeight: 1.7 }}>
              <strong>Роли:</strong> {availableClassRoles.length ? availableClassRoles.map((link) => `${link.role?.name || `#${link.id_role}`}${link.is_required ? ' *' : ''}`).join(', ') : 'не настроены'}<br />
              <strong>Параметры:</strong> {availableClassParameters.length ? availableClassParameters.map((link) => `${link.parameter?.name || `#${link.id_param}`}${link.is_required ? ' *' : ''}`).join(', ') : 'не настроены'}
            </div>
          </div>
        </div>
      </section>

      <section style={cardStyle}>
        <SectionTitle>6. Создать документ хозяйственной операции</SectionTitle>
        <form onSubmit={handleCreateOperation}>
          <FormGrid>
            <Field label="Тип операции"><select style={inputStyle} required value={selectedClassId} onChange={(e) => setSelectedClassId(e.target.value)}><option value="">Выберите тип</option>{classes.map((item) => <option key={item.id_ho_class} value={item.id_ho_class}>{item.name}</option>)}</select></Field>
            <Field label="Номер документа"><input style={inputStyle} value={operationForm.doc_number} onChange={(e) => setOperationForm({ ...operationForm, doc_number: e.target.value })} placeholder="Номер" /></Field>
            <Field label="Дата документа"><input style={inputStyle} type="date" value={operationForm.doc_date} onChange={(e) => setOperationForm({ ...operationForm, doc_date: e.target.value })} /></Field>
            <Field label="Начальная сумма"><input style={inputStyle} type="number" min="0" step="0.01" value={operationForm.total_amount} onChange={(e) => setOperationForm({ ...operationForm, total_amount: e.target.value })} /></Field>
            <button style={buttonStyle} disabled={busy || !selectedClassId}>Создать документ</button>
          </FormGrid>
        </form>
      </section>

      <section style={cardStyle}>
        <SectionTitle>7. Документы и их содержимое</SectionTitle>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 0.8fr) minmax(300px, 1.2fr)', gap: 22, alignItems: 'start' }}>
          <div>
            <Field label="Выберите документ"><select style={inputStyle} value={activeOperationId} onChange={(e) => setActiveOperationId(e.target.value)}><option value="">Выберите документ</option>{instances.map((item) => <option key={item.ho.id_ho} value={item.ho.id_ho}>#{item.ho.id_ho} — {item.ho.doc_number || 'без номера'} · {item.ho.ho_class?.name}</option>)}</select></Field>
            <div style={{ display: 'grid', gap: 10, marginTop: 14 }}>
              {instances.map((item) => <button key={item.ho.id_ho} type="button" onClick={() => setActiveOperationId(String(item.ho.id_ho))} style={{ ...secondaryButtonStyle, textAlign: 'left', background: String(item.ho.id_ho) === String(activeOperationId) ? '#E8E8E2' : '#fff' }}>
                <strong>#{item.ho.id_ho} {item.ho.doc_number || 'Без номера'}</strong><br /><span style={{ fontSize: 13 }}>{item.ho.ho_class?.name} · {item.ho.doc_date || 'дата не задана'} · {Number(item.ho.total_amount || 0).toFixed(2)}</span>
              </button>)}
              {!instances.length && <p style={{ color: '#777' }}>Документов пока нет.</p>}
            </div>
          </div>
          <div>
            {!selectedOperation ? <p style={{ color: '#777', marginTop: 0 }}>Выберите или создайте документ, чтобы добавить участников, параметры и позиции.</p> : <>
              <h3 style={{ margin: '0 0 8px', fontSize: 18 }}>{selectedOperation.ho.ho_class?.name} · документ #{selectedOperation.ho.id_ho}</h3>
              <p style={{ margin: '0 0 16px', color: '#666', fontSize: 14 }}>Сумма: {Number(selectedOperation.ho.total_amount || 0).toFixed(2)} · дата: {selectedOperation.ho.doc_date || '—'}</p>
              <div style={{ display: 'grid', gap: 12 }}>
                <form onSubmit={handleSetActor} style={{ ...panelStyle, padding: 14, display: 'grid', gap: 10 }}>
                  <strong>Добавить / изменить участника</strong>
                  <Field label="Роль"><select style={inputStyle} required value={actorForm.id_role} onChange={(e) => setActorForm({ ...actorForm, id_role: e.target.value })}><option value="">Выберите разрешённую роль</option>{(classes.find((item) => item.id_ho_class === selectedOperation.ho.id_ho_class) ? (classSchema.roles || []) : []).map((link) => <option key={link.id_role} value={link.id_role}>{link.role?.name || `Роль #${link.id_role}`}</option>)}</select></Field>
                  <Field label="Субъект"><select style={inputStyle} required value={actorForm.id_sxd} onChange={(e) => setActorForm({ ...actorForm, id_sxd: e.target.value })}><option value="">Выберите субъекта</option>{entities.map((item) => <option key={item.id_sxd} value={item.id_sxd}>{item.name}</option>)}</select></Field>
                  <button style={secondaryButtonStyle} disabled={busy}>Сохранить участника</button>
                </form>

                <form onSubmit={handleSetParameter} style={{ ...panelStyle, padding: 14, display: 'grid', gap: 10 }}>
                  <strong>Установить параметр</strong>
                  <Field label="Параметр"><select style={inputStyle} required value={operationParameterForm.id_param} onChange={(e) => setOperationParameterForm({ ...operationParameterForm, id_param: e.target.value, value: '', enum_value_id: '' })}><option value="">Выберите разрешённый параметр</option>{(classes.find((item) => item.id_ho_class === selectedOperation.ho.id_ho_class) ? (classSchema.parameters || []) : []).map((link) => <option key={link.id_param} value={link.id_param}>{link.parameter?.name || `Параметр #${link.id_param}`}</option>)}</select></Field>
                  {selectedParameter?.value_type === 'enum' ? <Field label="Значение перечисления"><select style={inputStyle} required value={operationParameterForm.enum_value_id} onChange={(e) => setOperationParameterForm({ ...operationParameterForm, enum_value_id: e.target.value })}><option value="">Выберите значение</option>{enumValues.map((item) => <option key={item.id_value} value={item.id_value}>{item.value}</option>)}</select></Field> : <Field label="Значение"><input style={inputStyle} required type={selectedParameter?.value_type === 'numeric' || selectedParameter?.value_type === 'integer' ? 'number' : selectedParameter?.value_type === 'datetime' ? 'datetime-local' : 'text'} step={selectedParameter?.value_type === 'integer' ? '1' : 'any'} value={operationParameterForm.value} onChange={(e) => setOperationParameterForm({ ...operationParameterForm, value: e.target.value })} /></Field>}
                  <button style={secondaryButtonStyle} disabled={busy || !selectedParameter}>Сохранить параметр</button>
                </form>

                <form onSubmit={handleAddPosition} style={{ ...panelStyle, padding: 14, display: 'grid', gap: 10 }}>
                  <strong>Добавить автомобиль в позиции</strong>
                  <Field label="Автомобиль"><select style={inputStyle} required value={positionForm.id_car} onChange={(e) => setPositionForm({ ...positionForm, id_car: e.target.value })}><option value="">Выберите автомобиль</option>{cars.map((item) => <option key={item.id_car} value={item.id_car}>{item.short_name} — {item.name}</option>)}</select></Field>
                  <FormGrid>
                    <Field label="Количество"><input style={inputStyle} required type="number" min="0.01" step="any" value={positionForm.quantity} onChange={(e) => setPositionForm({ ...positionForm, quantity: e.target.value })} /></Field>
                    <Field label="Цена за единицу"><input style={inputStyle} type="number" min="0" step="0.01" value={positionForm.price} onChange={(e) => setPositionForm({ ...positionForm, price: e.target.value })} /></Field>
                  </FormGrid>
                  <button style={secondaryButtonStyle} disabled={busy}>Добавить позицию</button>
                </form>
              </div>
              <div style={{ marginTop: 14, fontSize: 14, lineHeight: 1.8 }}>
                <strong>Участники:</strong> {selectedOperation.actors?.length ? selectedOperation.actors.map((item) => `${item.role?.name || 'Роль'}: ${item.entity?.name || 'субъект'}`).join('; ') : 'не заданы'}<br />
                <strong>Параметры:</strong> {selectedOperation.parameters?.length ? selectedOperation.parameters.map((item) => `${item.parameter?.name || 'Параметр'}: ${typeof item.value === 'object' ? item.value?.value || JSON.stringify(item.value) : item.value}`).join('; ') : 'не заданы'}<br />
                <strong>Позиции:</strong> {selectedOperation.positions?.length ? selectedOperation.positions.map((item) => `${item.car_name || `Автомобиль #${item.id_car}`}: ${item.quantity} × ${item.price ?? 'цена не задана'}`).join('; ') : 'не добавлены'}
              </div>
            </>}
          </div>
        </div>
      </section>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 28 }}><button style={secondaryButtonStyle} onClick={refresh} disabled={busy}>Обновить данные</button></div>
    </div>
  );
};

export default OperationsPage;
