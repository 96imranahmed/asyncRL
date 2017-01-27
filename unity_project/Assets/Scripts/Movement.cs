using UnityEngine;
using System.Collections;

public class Movement : MonoBehaviour {

    private Rigidbody droneRigidbody;
    public float forceMagnitude;
    private float discreteMagnitude;
    public Vector3 direction;
    private Vector3 newDirection;
    private Vector3 targetPosition;
    public bool toSend = false;
    private DataTrack dataTrackScript;

    private float groundSize;

    private bool discrete;

    private bool keyDown;

	// Use this for initialization
	void Start () {
        droneRigidbody = gameObject.GetComponent<Rigidbody>();
        GameObject ground = GameObject.Find("Ground");
        dataTrackScript = GameObject.FindGameObjectWithTag("Controller").GetComponent<DataTrack>();
        discrete = dataTrackScript.discrete;
        discreteMagnitude = dataTrackScript.discreteMagnitude;
        groundSize = ground.GetComponent<Collider>().bounds.size.x;
        if (discrete)
        {
            //TODO: fix for discrete
            Respawn();
        }
	}

    private void Respawn()
    {
        transform.position = new Vector3(0f, 0.5f, 0f);
    }

    // Update is called once per frame
    void Update()
    {
		//Debug.Log (toSend);
		//Debug.Log (direction);
        if (!Physics.Raycast(transform.position, -Vector3.up, Mathf.Infinity))
        {
            Debug.Log("raycast");
            Respawn();
        }
        if (!dataTrackScript.netControlled)
        {
            direction = Vector3.zero;
            direction = CreateDirectionFromInput();
        }
        if (discrete)
        {
            MoveDiscretely();
        }
        else
        {
            //Debug.Log("applying force");
            ApplyForce();
        }
        transform.position = new Vector3(transform.position.x, 0.5f, transform.position.z);
    }

    void LateUpdate()
    {
        //Debug.Log(dataTrackScript.netControlled);
        if (discrete)
        {
            transform.position = targetPosition;
        }
        if (dataTrackScript.netControlled && toSend)
        {
            //dataTrackScript.SendData ();
            //Debug.Log(direction);
            direction = Vector3.zero;
        }

    }

    private Vector3 CreateDirectionFromInput()
    {
        if (discrete)
        {
            direction = DiscreteDirection();
        }
        else
        {
            direction = ContinuousDirection();
        }
        return direction;
    }

    private Vector3 ContinuousDirection()
    {
        float inx = Input.GetAxis("Horizontal");
        float inz = Input.GetAxis("Vertical");
        direction = new Vector3(inx, 0, inz);
        return direction;
    }

    private Vector3 DiscreteDirection()
    {
        if (Input.GetKeyDown("w"))
        {
            direction = new Vector3(0f, 0f, 1f);
        }
        if (Input.GetKeyDown("a"))
        {
            direction = new Vector3(-1f, 0f, 0f);
        }
        if (Input.GetKeyDown("s"))
        {
            direction = new Vector3(0f, 0f, -1f);
        }
        if (Input.GetKeyDown("d"))
        {
            direction = new Vector3(1f, 0f, 0f);
        }
        return direction;
    }

    private void ApplyForce()
    {
		//Debug.Log (direction);
//		Debug.Log (discrete);
        newDirection = direction * forceMagnitude;
        droneRigidbody.AddForce(newDirection);
        // fix roll and pitch
        transform.eulerAngles = new Vector3(0f, transform.eulerAngles.y, 0f);
    }

    private void MoveDiscretely()
    {
        newDirection = direction * discreteMagnitude;
        bool outside = CheckOutside(transform.position + newDirection);
        if (!outside)
        {
            targetPosition = transform.position + newDirection;
            transform.position += newDirection;
        }
        //fix roll, pitch, yaw
        transform.eulerAngles = new Vector3(0f, 0f, 0f);
    }

    private bool CheckOutside(Vector3 newPosition)
    {
        float edgeDistance = groundSize / 2;
        float x = newPosition.x;
        float z = newPosition.z;
        if (Mathf.Abs(x) > edgeDistance) { return true; }
        if (Mathf.Abs(z) > edgeDistance) { return true; }
        return false;
    }
}
