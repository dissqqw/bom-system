const BASE_URL = 'http://127.0.0.1:5000';

const handleResponse = (res) => {
  if (!res.ok) {
    return res.json().then((data) => Promise.reject(data.error || 'Ошибка сервера'));
  }
  return res.json();
};

export const getTree = () => fetch(`${BASE_URL}/api/class/tree`).then(handleResponse);
export const getCars = () => fetch(`${BASE_URL}/api/cars`).then(handleResponse);
export const addCar = (data) => fetch(`${BASE_URL}/api/car/add`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const updateCar = (id, data) => fetch(`${BASE_URL}/api/car/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const deleteCar = (id) => fetch(`${BASE_URL}/api/car/${id}`, { method: 'DELETE' }).then(handleResponse);
export const getParameters = () => fetch(`${BASE_URL}/api/parameters`).then(handleResponse);
export const addParameter = (data) => fetch(`${BASE_URL}/api/parameter/add`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const updateParameter = (id, data) => fetch(`${BASE_URL}/api/parameter/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const deleteParameter = (id) => fetch(`${BASE_URL}/api/parameter/${id}`, { method: 'DELETE' }).then(handleResponse);
export const getEnumerations = () => fetch(`${BASE_URL}/api/enumerations`).then(handleResponse);
export const addEnumeration = (data) => fetch(`${BASE_URL}/api/enumeration/add`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const updateEnumeration = (id, data) => fetch(`${BASE_URL}/api/enumeration/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const deleteEnumeration = (id) => fetch(`${BASE_URL}/api/enumeration/${id}`, { method: 'DELETE' }).then(handleResponse);
export const getUnits = () => fetch(`${BASE_URL}/api/units`).then(handleResponse);
export const addUnit = (data) => fetch(`${BASE_URL}/api/unit/add`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const getClassDetails = (id) => fetch(`${BASE_URL}/api/class/${id}/parameters`).then(handleResponse);
export const addClass = (data) => fetch(`${BASE_URL}/api/class/add`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const deleteClass = (id) => fetch(`${BASE_URL}/api/class/${id}`, { method: 'DELETE' }).then(handleResponse);
export const linkParameterToClass = (classId, data) => fetch(`${BASE_URL}/api/class/${classId}/parameter/link`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const getCarValidation = (id) => fetch(`${BASE_URL}/api/car/${id}/validation/required`).then(handleResponse);
export const getCarDetails = (id) => fetch(`${BASE_URL}/api/car/${id}/details`).then(handleResponse);
export const setCarParameter = (carId, data) => fetch(`${BASE_URL}/api/car/${carId}/parameter`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const getClassParametersGrouped = (id) => fetch(`${BASE_URL}/api/class/${id}/parameters/grouped`).then(handleResponse);
export const createGroup = (classId, data) => fetch(`${BASE_URL}/api/class/${classId}/group`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const getClassEnums = (id) => fetch(`${BASE_URL}/api/class/${id}/enums`).then(handleResponse);
export const getClassGroups = (id) => fetch(`${BASE_URL}/api/class/${id}/groups`).then(handleResponse);

// Хозяйственные операции (4-е ТЗ)
export const getHoClasses = () => fetch(`${BASE_URL}/api/ho/classes`).then(handleResponse);
export const addHoClass = (data) => fetch(`${BASE_URL}/api/ho/class/add`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const getHoClassSchema = (id) => fetch(`${BASE_URL}/api/ho/class/${id}/schema`).then(handleResponse);
export const linkHoParameter = (classId, data) => fetch(`${BASE_URL}/api/ho/class/${classId}/parameter/link`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const linkHoRole = (classId, data) => fetch(`${BASE_URL}/api/ho/class/${classId}/role/link`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const getHoEntities = () => fetch(`${BASE_URL}/api/ho/entities`).then(handleResponse);
export const addHoEntity = (data) => fetch(`${BASE_URL}/api/ho/entities`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const getHoRoles = () => fetch(`${BASE_URL}/api/ho/roles`).then(handleResponse);
export const addHoRole = (data) => fetch(`${BASE_URL}/api/ho/roles`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const getHoParameters = () => fetch(`${BASE_URL}/api/ho/parameters`).then(handleResponse);
export const addHoParameter = (data) => fetch(`${BASE_URL}/api/ho/parameters`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const createHoInstance = (data) => fetch(`${BASE_URL}/api/ho/instance/add`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const getHoInstances = (classId) => fetch(`${BASE_URL}/api/ho/instances${classId ? `?id_ho_class=${classId}` : ''}`).then(handleResponse);
export const setHoActor = (id, data) => fetch(`${BASE_URL}/api/ho/${id}/actor`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const setHoParameter = (id, data) => fetch(`${BASE_URL}/api/ho/${id}/parameter`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const addHoPosition = (id, data) => fetch(`${BASE_URL}/api/ho/${id}/position/add`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(handleResponse);
export const getEnumerationValues = (id) => fetch(`${BASE_URL}/api/enumeration/${id}/values`).then(handleResponse);
